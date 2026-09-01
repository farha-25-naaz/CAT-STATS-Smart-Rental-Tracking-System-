"""Phase 5 — live ML endpoints backed by the ``ml_engine`` library.

* ``GET  /assets/{asset_id}/risk``            — score maintenance risk now, persist it
* ``POST /assets/{asset_id}/generate-summary`` — LLM alert summary, persist it

Both reuse the Phase 2 ingest write-paths (``ingest_risk`` / ``ingest_summary``)
rather than duplicating the DB logic.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException

from db import supabase
from ingest_routes import (
    _get_asset_or_404,
    _last_telemetry,
    ingest_risk,
    ingest_summary,
)
from ml_orchestration import (
    cost_config_for_asset,
    get_maintenance_risk_model,
    get_nl_summarizer,
)
from models import RiskIngest, SummaryIngest

router = APIRouter(prefix="/assets", tags=["ml"])


def _recent_anomaly_count(asset_id: str, days: int = 30) -> int:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows = (
        supabase.table("alerts")
        .select("alert_id")
        .eq("asset_id", asset_id)
        .gte("triggered_at", since)
        .execute()
        .data
    ) or []
    return len(rows)


def _latest_alert(asset_id: str) -> dict | None:
    rows = (
        supabase.table("alerts")
        .select("*")
        .eq("asset_id", asset_id)
        .order("triggered_at", desc=True)
        .limit(1)
        .execute()
        .data
    ) or []
    return rows[0] if rows else None


def _current_risk_row(asset_id: str) -> dict | None:
    rows = (
        supabase.table("maintenance_risk")
        .select("*")
        .eq("asset_id", asset_id)
        .limit(1)
        .execute()
        .data
    ) or []
    return rows[0] if rows else None


@router.get("/{asset_id}/risk")
def asset_risk(asset_id: str):
    """Score the asset's maintenance risk from its latest telemetry + anomaly
    history, upsert it into ``maintenance_risk`` (via ``/ingest/risk`` logic),
    and return the score."""
    _get_asset_or_404(asset_id)

    tele = _last_telemetry(asset_id)
    current_telemetry: dict[str, float] = {}
    for src, dst in (
        ("engine_hours", "engine_hours"),
        ("idle_hours", "idle_hours"),
        ("tilt_angle_deg", "tilt_angle_deg"),
    ):
        if tele.get(src) is not None:
            current_telemetry[dst] = float(tele[src])
    # hours_since_maintenance is not persisted in telemetry_logs -> omitted;
    # MaintenanceRiskModel.predict() tolerates the missing key.

    anomaly_count = _recent_anomaly_count(asset_id, days=30)

    model = get_maintenance_risk_model()
    try:
        risk = model.predict(
            asset_id,
            current_telemetry=current_telemetry,
            recent_anomaly_count=anomaly_count,
        )
    except KeyError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    persisted = ingest_risk(RiskIngest(**risk))

    return {
        "risk": risk,
        "inputs": {
            "current_telemetry": current_telemetry,
            "recent_anomaly_count": anomaly_count,
            "telemetry_found": bool(tele),
        },
        "persisted": persisted["maintenance_risk"],
    }


@router.post("/{asset_id}/generate-summary")
def asset_generate_summary(asset_id: str):
    """Gather asset + latest anomaly + current risk + cost rates, ask the
    NLSummarizer for a summary, then route it through ``/ingest/summary`` so it
    lands in ``alerts.summary`` (or the ``summaries`` fallback) exactly as before."""
    asset = _get_asset_or_404(asset_id)

    anomaly = _latest_alert(asset_id)
    risk = _current_risk_row(asset_id)
    cost_config = cost_config_for_asset(asset)

    summarizer = get_nl_summarizer()
    try:
        result = summarizer.summarize(
            asset_data=asset,
            anomaly=anomaly,
            risk=risk,
            cost_config=cost_config,
        )
    except Exception as exc:  # noqa: BLE001
        # No LLM client (GROQ_API_KEY unset), or an upstream LLM/API failure.
        raise HTTPException(status_code=503, detail=f"summarizer unavailable: {exc}")

    persisted = ingest_summary(
        SummaryIngest(
            asset_id=asset_id,
            summary=result["summary"],
            severity=result.get("severity"),
            generated_at=result.get("generated_at"),
        )
    )

    return {
        "summary": result,
        "inputs": {
            "anomaly_alert_id": anomaly.get("alert_id") if anomaly else None,
            "risk_tier": risk.get("risk_tier") if risk else None,
            "cost_config": cost_config,
        },
        "persisted": persisted,
    }
