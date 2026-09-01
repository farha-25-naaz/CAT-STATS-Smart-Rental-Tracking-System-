from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from db import supabase


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def check_overdue_assets() -> None:
    """Find ACTIVE assets past their expected return date, mark them OVERDUE
    and raise an unresolved OVERDUE alert if one does not already exist."""
    now = _now_iso()

    try:
        resp = (
            supabase.table("assets")
            .select("asset_id")
            .eq("status", "ACTIVE")
            .lt("check_in_date", now)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001 - demo scheduler, keep loop alive
        print(f"[overdue-checker] query failed: {exc}")
        return

    overdue_assets = resp.data or []
    if not overdue_assets:
        return

    for asset in overdue_assets:
        asset_id = asset["asset_id"]
        try:
            supabase.table("assets").update({"status": "OVERDUE"}).eq(
                "asset_id", asset_id
            ).execute()

            existing = (
                supabase.table("alerts")
                .select("alert_id")
                .eq("asset_id", asset_id)
                .eq("type", "OVERDUE")
                .is_("resolved_at", "null")
                .execute()
            )

            if not (existing.data or []):
                supabase.table("alerts").insert(
                    {
                        "asset_id": asset_id,
                        "type": "OVERDUE",
                        "severity": "HIGH",
                        "triggered_at": now,
                    }
                ).execute()
                print(f"[overdue-checker] asset {asset_id} marked OVERDUE + alert created")
            else:
                print(f"[overdue-checker] asset {asset_id} marked OVERDUE (alert exists)")
        except Exception as exc:  # noqa: BLE001
            print(f"[overdue-checker] failed for asset {asset_id}: {exc}")


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        check_overdue_assets,
        trigger="interval",
        seconds=60,
        id="overdue_checker",
        replace_existing=True,
        next_run_time=datetime.now(timezone.utc),
    )
    scheduler.start()
    return scheduler
