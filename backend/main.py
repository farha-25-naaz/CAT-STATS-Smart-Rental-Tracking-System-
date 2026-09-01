import os
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from db import supabase
from models import (
    ActionResponse,
    CheckInRequest,
    CheckOutRequest,
    DayUsage,
    LiveAsset,
)
from catalog_routes import router as catalog_router
from demo_routes import router as demo_router
from forecast_routes import router as forecast_router
from ingest_routes import router as ingest_router
from ml_orchestration import load_or_train_models, refresh_site_centroids
from ml_routes import router as ml_router
from safety_routes import router as safety_router
from scheduler import start_scheduler
from websocket_manager import manager

_scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _scheduler
    load_or_train_models()
    _scheduler = start_scheduler()
    # Sites rarely change; re-pull their centroids every 15 min so the
    # AnomalyDetector geofence rule tracks live edits without a restart.
    _scheduler.add_job(
        refresh_site_centroids,
        trigger="interval",
        minutes=15,
        id="site_centroid_refresh",
        replace_existing=True,
    )
    yield
    if _scheduler:
        _scheduler.shutdown(wait=False)


app = FastAPI(title="CAT-STATS Smart Rental Tracking System", lifespan=lifespan)

# Comma-separated list in CORS_ALLOW_ORIGINS, or "*" to allow any (dev default).
_cors_env = os.getenv("CORS_ALLOW_ORIGINS", "*").strip()
_cors_origins = ["*"] if _cors_env == "*" else [o.strip() for o in _cors_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest_router)
app.include_router(safety_router)
app.include_router(ml_router)
app.include_router(demo_router)
app.include_router(catalog_router)
app.include_router(forecast_router)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_asset_or_404(asset_id: str) -> dict:
    resp = supabase.table("assets").select("*").eq("asset_id", asset_id).execute()
    rows = resp.data or []
    if not rows:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")
    return rows[0]


@app.get("/")
def health_check():
    return {"status": "ok"}


@app.websocket("/ws/live")
async def ws_live(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # We don't act on inbound messages; this loop only detects disconnect.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:  # noqa: BLE001 - any transport error means the client is gone
        manager.disconnect(websocket)


def _latest_by_asset(rows: List[dict], order_key: str) -> dict:
    """Collapse a DESC-ordered row list to {asset_id: first (=newest) row}."""
    latest: dict = {}
    for row in rows:
        aid = row.get("asset_id")
        if aid and aid not in latest:
            latest[aid] = row
    return latest


@app.get("/assets/live", response_model=List[LiveAsset])
def assets_live():
    assets = (supabase.table("assets").select("*").execute().data) or []

    sites = (supabase.table("sites").select("*").execute().data) or []
    site_by_id = {s["site_id"]: s for s in sites}

    risk_rows = (
        supabase.table("maintenance_risk").select("*").execute().data
    ) or []
    risk_by_asset = {r["asset_id"]: r for r in risk_rows}

    tele_rows = (
        supabase.table("telemetry_logs")
        .select("*")
        .order("recorded_at", desc=True)
        .limit(5000)
        .execute()
        .data
    ) or []
    tele_by_asset = _latest_by_asset(tele_rows, "recorded_at")

    alert_rows = (
        supabase.table("alerts")
        .select("*")
        .is_("resolved_at", "null")
        .order("triggered_at", desc=True)
        .limit(2000)
        .execute()
        .data
    ) or []
    alert_by_asset = _latest_by_asset(alert_rows, "triggered_at")

    result: List[LiveAsset] = []
    for asset in assets:
        aid = asset["asset_id"]
        tele = tele_by_asset.get(aid, {})
        alert = alert_by_asset.get(aid, {})
        risk = risk_by_asset.get(aid, {})
        site = site_by_id.get(asset.get("current_site_id"), {})
        result.append(
            LiveAsset(
                asset_id=aid,
                type=asset.get("type"),
                status=asset.get("status"),
                current_site_id=asset.get("current_site_id"),
                site_name=site.get("site_name"),
                current_operator_id=asset.get("current_operator_id"),
                check_out_date=asset.get("check_out_date"),
                check_in_date=asset.get("check_in_date"),
                lat=tele.get("lat"),
                lng=tele.get("lng"),
                recorded_at=tele.get("recorded_at"),
                speed_kmh=tele.get("speed_kmh"),
                tilt_angle_deg=tele.get("tilt_angle_deg"),
                engine_hours=tele.get("engine_hours"),
                idle_hours=tele.get("idle_hours"),
                fuel_level_pct=tele.get("fuel_level_pct"),
                is_anomaly=tele.get("is_anomaly"),
                latest_anomaly_type=alert.get("type"),
                latest_anomaly_reason=alert.get("summary"),
                latest_anomaly_severity=alert.get("severity"),
                risk_tier=risk.get("risk_tier"),
                risk_score=risk.get("risk_score"),
                rental_rate_per_day=asset.get("rental_rate_per_day"),
                idle_cost_per_hour=asset.get("idle_cost_per_hour"),
            )
        )
    return result


@app.post("/check-out", response_model=ActionResponse)
def check_out(body: CheckOutRequest):
    asset = _get_asset_or_404(body.asset_id)

    site = (
        supabase.table("sites")
        .select("site_id")
        .eq("site_id", body.site_id)
        .execute()
        .data
    ) or []
    if not site:
        raise HTTPException(
            status_code=400, detail=f"Site {body.site_id} not found"
        )

    if asset.get("status") != "UNASSIGNED":
        raise HTTPException(
            status_code=400,
            detail=(
                f"Asset {body.asset_id} cannot be checked out "
                f"(current status: {asset.get('status')})"
            ),
        )

    supabase.table("assets").update(
        {
            "status": "ACTIVE",
            "current_site_id": body.site_id,
            "current_operator_id": body.operator_id,
            "check_out_date": _now_iso(),
            "check_in_date": body.check_in_date.isoformat(),
        }
    ).eq("asset_id", body.asset_id).execute()

    return ActionResponse(
        asset_id=body.asset_id,
        status="ACTIVE",
        message="Asset checked out",
    )


@app.post("/check-in", response_model=ActionResponse)
def check_in(body: CheckInRequest):
    _get_asset_or_404(body.asset_id)
    now = _now_iso()

    supabase.table("assets").update(
        {
            "status": "UNASSIGNED",
            "current_site_id": None,
            "current_operator_id": None,
            "check_in_date": now,
        }
    ).eq("asset_id", body.asset_id).execute()

    overdue_alerts = (
        supabase.table("alerts")
        .select("alert_id")
        .eq("asset_id", body.asset_id)
        .eq("type", "OVERDUE")
        .is_("resolved_at", "null")
        .execute()
        .data
    ) or []
    if overdue_alerts:
        supabase.table("alerts").update({"resolved_at": now}).eq(
            "asset_id", body.asset_id
        ).eq("type", "OVERDUE").is_("resolved_at", "null").execute()

    return ActionResponse(
        asset_id=body.asset_id,
        status="UNASSIGNED",
        message="Asset checked in",
    )


@app.get("/usage-summary", response_model=List[DayUsage])
def usage_summary(
    asset_id: str = Query(...),
    days: int = Query(7, ge=1),
):
    _get_asset_or_404(asset_id)

    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows = (
        supabase.table("telemetry_logs")
        .select("recorded_at,engine_hours,idle_hours,fuel_level_pct")
        .eq("asset_id", asset_id)
        .gte("recorded_at", since)
        .order("recorded_at", desc=False)
        .execute()
        .data
    ) or []

    by_day: dict = defaultdict(list)
    for row in rows:
        recorded_at = row.get("recorded_at")
        if not recorded_at:
            continue
        day = str(recorded_at)[:10]
        by_day[day].append(row)

    summary: List[DayUsage] = []
    for day in sorted(by_day):
        day_rows = by_day[day]

        engine_vals = [
            r["engine_hours"] for r in day_rows if r.get("engine_hours") is not None
        ]
        idle_vals = [
            r["idle_hours"] for r in day_rows if r.get("idle_hours") is not None
        ]
        fuel_vals = [
            r["fuel_level_pct"]
            for r in day_rows
            if r.get("fuel_level_pct") is not None
        ]

        # engine_hours / idle_hours are cumulative lifetime totals -> diff within day
        engine_delta = (
            engine_vals[-1] - engine_vals[0] if len(engine_vals) >= 2 else 0.0
        )
        idle_delta = idle_vals[-1] - idle_vals[0] if len(idle_vals) >= 2 else 0.0
        avg_fuel = sum(fuel_vals) / len(fuel_vals) if fuel_vals else None

        summary.append(
            DayUsage(
                date=day,
                engine_hours_delta=round(engine_delta, 3),
                idle_hours_delta=round(idle_delta, 3),
                avg_fuel_level_pct=round(avg_fuel, 2) if avg_fuel is not None else None,
            )
        )

    return summary
