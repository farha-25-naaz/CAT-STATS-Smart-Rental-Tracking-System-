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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest_router)
app.include_router(safety_router)
app.include_router(ml_router)


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


@app.get("/assets/live", response_model=List[LiveAsset])
def assets_live():
    assets = (supabase.table("assets").select("*").execute().data) or []

    result: List[LiveAsset] = []
    for asset in assets:
        latest = (
            supabase.table("telemetry_logs")
            .select("lat,lng,recorded_at")
            .eq("asset_id", asset["asset_id"])
            .order("recorded_at", desc=True)
            .limit(1)
            .execute()
            .data
        ) or []
        tele = latest[0] if latest else {}
        result.append(
            LiveAsset(
                asset_id=asset["asset_id"],
                type=asset.get("type"),
                status=asset.get("status"),
                current_site_id=asset.get("current_site_id"),
                current_operator_id=asset.get("current_operator_id"),
                check_in_date=asset.get("check_in_date"),
                lat=tele.get("lat"),
                lng=tele.get("lng"),
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
