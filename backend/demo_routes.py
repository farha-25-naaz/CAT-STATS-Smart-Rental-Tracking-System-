"""Phase 6 — demo safety net.

* ``GET  /health``       — liveness + DB reachability + live WS connection count
* ``POST /demo/replay``  — replay a canned scenario through the REAL ingest /
  broadcast path, so a dead live telemetry feed can't sink a demo.
"""

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from db import supabase
from ingest_routes import ingest_anomaly, ingest_telemetry
from models import AnomalyIngest, AnomalyType, DemoReplayRequest, TelemetryIngest
from websocket_manager import manager

router = APIRouter(tags=["demo"])

# Bengaluru fallback coordinate when the asset has no site centroid on file.
_FALLBACK_LAT, _FALLBACK_LNG = 12.9716, 77.5946

# Pacing between replay steps so a live audience sees each stage land in order,
# mimicking the real telemetry -> detection -> lockout timeline.
_STEP_DELAY_S = 1.5


def _now() -> datetime:
    return datetime.now(timezone.utc)


@router.get("/health")
def health():
    db_connected = True
    try:
        supabase.table("assets").select("asset_id").limit(1).execute()
    except Exception:  # noqa: BLE001 - any failure means DB is unreachable
        db_connected = False

    return {
        "status": "ok",
        "db_connected": db_connected,
        "active_websocket_connections": len(manager.active_connections),
    }


def _asset_site_centroid(asset_id: str) -> tuple[float, float]:
    asset = (
        supabase.table("assets")
        .select("current_site_id")
        .eq("asset_id", asset_id)
        .execute()
        .data
    ) or []
    site_id = asset[0].get("current_site_id") if asset else None
    if site_id:
        site = (
            supabase.table("sites")
            .select("center_lat,center_lng")
            .eq("site_id", site_id)
            .execute()
            .data
        ) or []
        if site and site[0].get("center_lat") is not None:
            return float(site[0]["center_lat"]), float(site[0]["center_lng"])
    return _FALLBACK_LAT, _FALLBACK_LNG


@router.post("/demo/replay")
async def demo_replay(body: DemoReplayRequest):
    """Play a scripted scenario through the same handlers a live feed would hit.

    ``safety_breach``: a high-tilt telemetry row followed by a CRITICAL
    SAFETY_HAZARD anomaly — drives the real geofence/lockout logic, the
    ``assets.status -> SAFETY_LOCKOUT`` write, and the WS broadcasts.
    """
    if body.scenario != "safety_breach":
        raise HTTPException(
            status_code=400,
            detail=f"Unknown scenario {body.scenario!r} (supported: 'safety_breach')",
        )

    asset = (
        supabase.table("assets")
        .select("asset_id")
        .eq("asset_id", body.asset_id)
        .execute()
        .data
    ) or []
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset {body.asset_id} not found")

    lat, lng = _asset_site_centroid(body.asset_id)
    now = _now()

    await manager.broadcast(
        {"event": "DEMO_REPLAY_START", "scenario": body.scenario, "asset_id": body.asset_id}
    )
    await asyncio.sleep(_STEP_DELAY_S)

    telemetry_result = await ingest_telemetry(
        TelemetryIngest(
            asset_id=body.asset_id,
            lat=lat,
            lng=lng,
            speed_kmh=6.0,
            tilt_angle=35.0,  # > 30° SAFETY_HAZARD threshold
            timestamp=now,
        )
    )
    await asyncio.sleep(_STEP_DELAY_S)

    anomaly_result = await ingest_anomaly(
        AnomalyIngest(
            asset_id=body.asset_id,
            is_anomaly=True,
            anomaly_type=AnomalyType.SAFETY_HAZARD,
            anomaly_score=1.0,
            detected_at=now,
            reason="Demo replay: tilt 35.0° exceeds 30° limit",
        )
    )

    await asyncio.sleep(_STEP_DELAY_S)
    await manager.broadcast(
        {"event": "DEMO_REPLAY_END", "scenario": body.scenario, "asset_id": body.asset_id}
    )

    return {
        "scenario": body.scenario,
        "asset_id": body.asset_id,
        "steps": ["DEMO_REPLAY_START", "telemetry", "anomaly", "DEMO_REPLAY_END"],
        "telemetry": telemetry_result,
        "anomaly": anomaly_result,
        "expected_state": {"assets.status": "SAFETY_LOCKOUT"},
    }
