"""Phase 6 — realistic demo seed data.

Idempotent: assets/sites are upserted on their PKs; telemetry_logs / alerts /
maintenance_risk rows for the seeded asset ids are deleted and re-inserted.

    python seed_demo_data.py
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from db import supabase

RNG = random.Random(42)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


# ── Sites (Bengaluru area, offset per site) ─────────────────────────────────
BLR_LAT, BLR_LNG = 12.9716, 77.5946
SITES = [
    {"site_id": "S001", "site_name": "Whitefield Yard",     "center_lat": BLR_LAT + 0.045, "center_lng": BLR_LNG + 0.075, "geofence_radius_meters": 500},
    {"site_id": "S002", "site_name": "Electronic City Site", "center_lat": BLR_LAT - 0.090, "center_lng": BLR_LNG + 0.010, "geofence_radius_meters": 450},
    {"site_id": "S003", "site_name": "Hebbal Depot",         "center_lat": BLR_LAT + 0.110, "center_lng": BLR_LNG - 0.010, "geofence_radius_meters": 600},
    {"site_id": "S004", "site_name": "Peenya Industrial",    "center_lat": BLR_LAT + 0.060, "center_lng": BLR_LNG - 0.075, "geofence_radius_meters": 500},
]
SITE_CENTROIDS = {s["site_id"]: (s["center_lat"], s["center_lng"]) for s in SITES}

# ── Assets ─────────────────────────────────────────────────────────────────
# (asset_id, type, site, status)  — 2 rows are deliberately ACTIVE with a
# past check_in_date so the overdue checker flips them to OVERDUE on its next run.
_ASSET_DEFS = [
    ("EXC-101", "Excavator",  "S001", "ACTIVE"),
    ("EXC-102", "Excavator",  "S002", "ACTIVE"),      # overdue (past check_in_date)
    ("CRN-201", "Crane",      "S001", "ACTIVE"),
    ("CRN-202", "Crane",      "S003", "IDLE"),
    ("BLD-301", "Bulldozer",  "S003", "ACTIVE"),      # overdue (past check_in_date)
    ("BLD-302", "Bulldozer",  "S004", "IDLE"),
    ("LDR-401", "Loader",     "S002", "ACTIVE"),
    ("LDR-402", "Loader",     None,   "UNASSIGNED"),
    ("DMP-501", "Dump Truck", "S004", "ACTIVE"),
    ("DMP-502", "Dump Truck", None,   "UNASSIGNED"),
]
OVERDUE_ASSETS = {"EXC-102", "BLD-301"}
# Assets that get a historical telemetry trail.
TELEMETRY_ASSETS = ["EXC-101", "CRN-201", "BLD-301", "LDR-401", "DMP-501"]

ASSET_IDS = [a[0] for a in _ASSET_DEFS]


def _build_assets() -> list[dict]:
    now = _now()
    rows = []
    for asset_id, atype, site_id, status in _ASSET_DEFS:
        row = {
            "asset_id": asset_id,
            "type": atype,
            "status": status,
            "current_site_id": site_id,
            "current_operator_id": f"OP-{RNG.randint(1000, 9999)}" if site_id else None,
            "rental_rate_per_day": round(RNG.uniform(400, 900), 2),
            "idle_cost_per_hour": round(RNG.uniform(15, 35), 2),
        }
        if site_id:
            row["check_out_date"] = _iso(now - timedelta(days=RNG.randint(3, 12)))
            if asset_id in OVERDUE_ASSETS:
                # expected return already passed -> overdue checker will catch it
                row["check_in_date"] = _iso(now - timedelta(days=RNG.randint(1, 3), hours=RNG.randint(0, 12)))
            elif status != "UNASSIGNED":
                row["check_in_date"] = _iso(now + timedelta(days=RNG.randint(2, 10)))
        rows.append(row)
    return rows


def _build_telemetry() -> list[dict]:
    now = _now()
    rows: list[dict] = []
    for asset_id in TELEMETRY_ASSETS:
        site_id = next((a[2] for a in _ASSET_DEFS if a[0] == asset_id), None)
        clat, clng = SITE_CENTROIDS.get(site_id, (BLR_LAT, BLR_LNG))
        engine_h = RNG.uniform(800, 2500)
        idle_h = engine_h * RNG.uniform(0.15, 0.30)
        fuel = RNG.uniform(60, 95)
        n = 25  # ~100-125 rows total across 4-5 assets
        for i in range(n):
            # oldest -> newest, spread across the past 7 days
            ts = now - timedelta(days=7) + timedelta(minutes=i * (7 * 24 * 60 // n))
            working = RNG.random() < 0.75
            engine_h += RNG.uniform(0.2, 0.7) if working else RNG.uniform(0.0, 0.05)
            idle_h += RNG.uniform(0.02, 0.15) if working else RNG.uniform(0.1, 0.3)
            fuel -= RNG.uniform(0.5, 3.0)
            if fuel < 15:
                fuel = RNG.uniform(80, 95)  # refuelled
            rows.append({
                "asset_id": asset_id,
                "recorded_at": _iso(ts),
                "lat": round(clat + RNG.gauss(0, 0.0006), 6),
                "lng": round(clng + RNG.gauss(0, 0.0006), 6),
                "engine_hours": round(engine_h, 2),
                "idle_hours": round(idle_h, 2),
                "fuel_level_pct": round(fuel, 1),
                "speed_kmh": round(RNG.uniform(3, 16), 1) if working else 0.0,
                "tilt_angle_deg": round(RNG.uniform(0, 12), 1),
                "is_anomaly": False,
            })
    return rows


def _build_alerts() -> list[dict]:
    now = _now()
    return [
        {
            "asset_id": "LDR-401",
            "type": "EXCESSIVE_IDLE",
            "severity": "HIGH",
            "triggered_at": _iso(now - timedelta(hours=6)),
        },
        {
            "asset_id": "CRN-201",
            "type": "SAFETY_HAZARD",
            "severity": "CRITICAL",
            "triggered_at": _iso(now - timedelta(hours=2)),
        },
    ]


def _clean(table: str, rows_desc: str) -> None:
    supabase.table(table).delete().in_("asset_id", ASSET_IDS).execute()
    print(f"  cleared prior {rows_desc}")


def main() -> None:
    print("Seeding demo data...")

    supabase.table("sites").upsert(SITES, on_conflict="site_id").execute()
    print(f"  sites: upserted {len(SITES)}")

    assets = _build_assets()
    supabase.table("assets").upsert(assets, on_conflict="asset_id").execute()
    print(f"  assets: upserted {len(assets)} "
          f"({sum(1 for a in assets if a['asset_id'] in OVERDUE_ASSETS)} pre-dated for OVERDUE)")

    _clean("maintenance_risk", "maintenance_risk rows")
    _clean("alerts", "alerts")
    _clean("telemetry_logs", "telemetry_logs")

    telem = _build_telemetry()
    for i in range(0, len(telem), 200):
        supabase.table("telemetry_logs").insert(telem[i:i + 200]).execute()
    print(f"  telemetry_logs: inserted {len(telem)} rows "
          f"across {len(TELEMETRY_ASSETS)} assets over 7 days")

    alerts = _build_alerts()
    supabase.table("alerts").insert(alerts).execute()
    print(f"  alerts: inserted {len(alerts)} "
          f"({', '.join(a['type'] for a in alerts)})")

    print("Done.")


if __name__ == "__main__":
    main()
