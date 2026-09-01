"""Phase 4 — safety lockout override / clearance flow."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from db import supabase
from models import SafetyOverrideRequest
from security import verify_pin
from websocket_manager import manager

router = APIRouter(prefix="/api/v1/safety", tags=["safety"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _latest_unresolved_critical_alert(asset_id: str) -> dict | None:
    """Most recent unresolved CRITICAL alert for an asset.

    Same ORDER BY triggered_at DESC LIMIT 1 pattern proven in Phase 2's
    summary-attachment logic, with the CRITICAL + unresolved filters added.
    """
    rows = (
        supabase.table("alerts")
        .select("*")
        .eq("asset_id", asset_id)
        .eq("severity", "CRITICAL")
        .is_("resolved_at", "null")
        .order("triggered_at", desc=True)
        .limit(1)
        .execute()
        .data
    ) or []
    return rows[0] if rows else None


@router.post("/override")
async def safety_override(body: SafetyOverrideRequest):
    supervisor = (
        supabase.table("supervisors")
        .select("*")
        .eq("supervisor_id", body.supervisor_id)
        .execute()
        .data
    ) or []
    if not supervisor or not verify_pin(body.pin, supervisor[0].get("pin_hash")):
        raise HTTPException(
            status_code=401, detail="Invalid supervisor ID or PIN"
        )

    asset = (
        supabase.table("assets")
        .select("*")
        .eq("asset_id", body.asset_id)
        .execute()
        .data
    ) or []
    if not asset:
        raise HTTPException(
            status_code=404, detail=f"Asset {body.asset_id} not found"
        )
    if asset[0].get("status") != "SAFETY_LOCKOUT":
        raise HTTPException(
            status_code=409, detail="Asset is not currently locked out"
        )

    now = _now_iso()

    supabase.table("assets").update({"status": body.resume_status}).eq(
        "asset_id", body.asset_id
    ).execute()

    alert = _latest_unresolved_critical_alert(body.asset_id)
    resolved_alert = None
    if alert:
        resolved_alert = (
            supabase.table("alerts")
            .update(
                {
                    "resolved_at": now,
                    "resolved_by": body.supervisor_id,
                    "resolution_note": body.resolution_note,
                    "override_pin_used": True,
                }
            )
            .eq("alert_id", alert["alert_id"])
            .execute()
            .data[0]
        )

    await manager.broadcast(
        {
            "event": "LOCKOUT_CLEARED",
            "asset_id": body.asset_id,
            "cleared_by": body.supervisor_id,
        }
    )

    return {
        "status": "cleared",
        "asset_id": body.asset_id,
        "resume_status": body.resume_status,
        "cleared_by": body.supervisor_id,
        "resolved_alert_id": resolved_alert["alert_id"] if resolved_alert else None,
    }


@router.get("/active-lockouts")
def active_lockouts():
    assets = (
        supabase.table("assets")
        .select("*")
        .eq("status", "SAFETY_LOCKOUT")
        .execute()
        .data
    ) or []

    result = []
    for asset in assets:
        result.append(
            {
                "asset_id": asset["asset_id"],
                "type": asset.get("type"),
                "status": asset.get("status"),
                "current_site_id": asset.get("current_site_id"),
                "current_operator_id": asset.get("current_operator_id"),
                "critical_alert": _latest_unresolved_critical_alert(
                    asset["asset_id"]
                ),
            }
        )
    return result
