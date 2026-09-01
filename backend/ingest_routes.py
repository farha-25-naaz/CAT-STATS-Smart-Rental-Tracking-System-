"""Phase 2 ingest endpoints — receive outputs from the ML pipeline
(AnomalyDetector, MaintenanceRiskModel, NLSummarizer)."""

import math
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from db import supabase
from models import AnomalyIngest, RiskIngest, SummaryIngest, TelemetryIngest
from websocket_manager import manager

router = APIRouter(prefix="/ingest", tags=["ingest"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between two lat/lng points, in metres."""
    r = 6371000.0  # mean Earth radius, metres
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(a))


def _get_asset_or_404(asset_id: str) -> dict:
    rows = (
        supabase.table("assets").select("*").eq("asset_id", asset_id).execute().data
    ) or []
    if not rows:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")
    return rows[0]


def _last_telemetry(asset_id: str) -> dict:
    rows = (
        supabase.table("telemetry_logs")
        .select("*")
        .eq("asset_id", asset_id)
        .order("recorded_at", desc=True)
        .limit(1)
        .execute()
        .data
    ) or []
    return rows[0] if rows else {}


@router.post("/telemetry")
async def ingest_telemetry(body: TelemetryIngest):
    asset = _get_asset_or_404(body.asset_id)
    prev = _last_telemetry(body.asset_id)

    def carry(field: str, payload_value):
        if payload_value is not None:
            return payload_value
        return prev.get(field)

    row = {
        "asset_id": body.asset_id,
        "recorded_at": body.timestamp.isoformat(),
        "lat": body.lat,
        "lng": body.lng,
        "speed_kmh": body.speed_kmh,
        "tilt_angle_deg": body.tilt_angle,
        "engine_hours": carry("engine_hours", body.engine_hours),
        "idle_hours": carry("idle_hours", body.idle_hours),
        "fuel_level_pct": carry("fuel_level_pct", body.fuel_level_pct),
        "is_anomaly": False,
    }
    inserted = supabase.table("telemetry_logs").insert(row).execute().data[0]

    # --- Geofence breach: caller-supplied flag OR server-side centroid check ---
    is_geofence_breach = bool(body.is_geofence_breach)
    site_id = asset.get("current_site_id")
    if site_id:
        site_rows = (
            supabase.table("sites")
            .select("center_lat,center_lng,geofence_radius_meters")
            .eq("site_id", site_id)
            .execute()
            .data
        ) or []
        site = site_rows[0] if site_rows else {}
        center_lat = site.get("center_lat")
        center_lng = site.get("center_lng")
        radius = site.get("geofence_radius_meters")
        if center_lat is not None and center_lng is not None and radius is not None:
            distance_m = haversine_distance(
                body.lat, body.lng, center_lat, center_lng
            )
            if distance_m > radius:
                is_geofence_breach = True
    # No current_site_id -> can't breach a geofence you're not assigned to.
    # That's UNAUTHORIZED_MOVEMENT, handled by the ML layer separately.

    alert = None
    if is_geofence_breach:
        alert = (
            supabase.table("alerts")
            .insert(
                {
                    "asset_id": body.asset_id,
                    "type": "GEOFENCE_BREACH",
                    "severity": "HIGH",
                    "triggered_at": body.timestamp.isoformat(),
                }
            )
            .execute()
            .data[0]
        )
        if body.tilt_angle is not None and body.tilt_angle > 30.0:
            supabase.table("assets").update({"status": "SAFETY_LOCKOUT"}).eq(
                "asset_id", body.asset_id
            ).execute()

    payload = body.model_dump(mode="json")
    payload["event"] = "TELEMETRY"
    payload["is_geofence_breach"] = is_geofence_breach
    await manager.broadcast(payload)

    return {"telemetry": inserted, "alert": alert}


@router.post("/anomaly")
async def ingest_anomaly(body: AnomalyIngest):
    _get_asset_or_404(body.asset_id)

    severity = "CRITICAL" if body.anomaly_type.value == "SAFETY_HAZARD" else "HIGH"

    alert = (
        supabase.table("alerts")
        .insert(
            {
                "asset_id": body.asset_id,
                "type": body.anomaly_type.value,
                "severity": severity,
                "triggered_at": body.detected_at.isoformat(),
            }
        )
        .execute()
        .data[0]
    )

    if severity == "CRITICAL":
        supabase.table("assets").update({"status": "SAFETY_LOCKOUT"}).eq(
            "asset_id", body.asset_id
        ).execute()
        await manager.broadcast(
            {
                "event": "SAFETY_LOCKOUT",
                "asset_id": body.asset_id,
                "anomaly_type": body.anomaly_type.value,
                "reason": body.reason,
            }
        )

    last = _last_telemetry(body.asset_id)
    if last:
        supabase.table("telemetry_logs").update({"is_anomaly": True}).eq(
            "log_id", last["log_id"]
        ).execute()

    return {"alert": alert, "telemetry_flagged": bool(last)}


@router.post("/risk")
def ingest_risk(body: RiskIngest):
    _get_asset_or_404(body.asset_id)

    record = {
        "asset_id": body.asset_id,
        "risk_score": body.risk_score,
        "risk_tier": body.risk_tier,
        "predicted_failure_window_days": body.predicted_failure_window_days,
        "contributing_factors": body.contributing_factors,
        "updated_at": _now_iso(),
    }
    upserted = (
        supabase.table("maintenance_risk")
        .upsert(record, on_conflict="asset_id")
        .execute()
        .data[0]
    )
    return {"maintenance_risk": upserted}


@router.post("/summary")
def ingest_summary(body: SummaryIngest):
    _get_asset_or_404(body.asset_id)

    latest_alert = (
        supabase.table("alerts")
        .select("alert_id")
        .eq("asset_id", body.asset_id)
        .order("triggered_at", desc=True)
        .limit(1)
        .execute()
        .data
    ) or []

    if latest_alert:
        updated = (
            supabase.table("alerts")
            .update({"summary": body.summary})
            .eq("alert_id", latest_alert[0]["alert_id"])
            .execute()
            .data[0]
        )
        return {"target": "alert", "alert": updated}

    generated_at = (
        body.generated_at.isoformat() if body.generated_at else _now_iso()
    )
    logged = (
        supabase.table("summaries")
        .insert(
            {
                "asset_id": body.asset_id,
                "summary": body.summary,
                "severity": body.severity.value if body.severity else None,
                "generated_at": generated_at,
            }
        )
        .execute()
        .data[0]
    )
    return {"target": "summaries", "summary": logged}
