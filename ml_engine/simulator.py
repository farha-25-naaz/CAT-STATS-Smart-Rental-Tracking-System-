"""
Batch historical telemetry simulator for ML model training and seed data.

Generates synthetic construction-equipment telemetry matching Person 2's
``telemetry_logs`` DB schema, with controllable anomaly injection.

Usage::

    python -m ml_engine.simulator          # writes sample_data/telemetry.csv
    python -m ml_engine.simulator --help   # CLI options
"""

from __future__ import annotations

import math
import os
import random
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

# ── Constants ────────────────────────────────────────────────────────────────

EQUIPMENT_TYPES = ["Excavator", "Crane", "Loader", "Dump Truck", "Bulldozer"]

# DB-ready columns (matches Person 2's telemetry_logs table)
# NOTE: engine_hours and idle_hours are CUMULATIVE running totals
# (e.g., 1523.5 = total lifetime hours at this timestamp), NOT per-row deltas.
# Person 1's usage charts and Person 2's DB writes must assume the same.
DB_COLUMNS = [
    "asset_id",
    "recorded_at",
    "lat",
    "lng",
    "engine_hours",
    "idle_hours",
    "fuel_level_pct",
    "tilt_angle_deg",
    "speed_kmh",
    "is_anomaly",
]

# Internal-only columns (used by ML models, NOT persisted to DB)
INTERNAL_COLUMNS = [
    "equipment_type",
    "site_id",
    "engine_active",
    "hours_since_maintenance",
]

ANOMALY_TYPES = [
    "UNAUTHORIZED_MOVEMENT",
    "EXCESSIVE_IDLE",
    "GEOFENCE_BREACH",
    "SAFETY_HAZARD",
    "IRREGULAR_USAGE",
]

# Default cost lookup per equipment type
DEFAULT_COST_CONFIG: dict[str, dict[str, float]] = {
    "Excavator":  {"rental_rate_per_day": 850.0,  "idle_cost_per_hour": 26.25},
    "Crane":      {"rental_rate_per_day": 1200.0, "idle_cost_per_hour": 35.00},
    "Loader":     {"rental_rate_per_day": 650.0,  "idle_cost_per_hour": 20.00},
    "Dump Truck": {"rental_rate_per_day": 500.0,  "idle_cost_per_hour": 18.50},
    "Bulldozer":  {"rental_rate_per_day": 950.0,  "idle_cost_per_hour": 28.75},
}

# Site definitions: (center_lat, center_lng, name)
DEFAULT_SITES = {
    "S001": (28.6139, 77.2090, "Delhi HQ"),
    "S002": (19.0760, 72.8777, "Mumbai Yard"),
    "S003": (12.9716, 77.5946, "Bangalore Depot"),
    "S004": (22.5726, 88.3639, "Kolkata Port"),
    "S005": (17.3850, 78.4867, "Hyderabad Site A"),
    "S006": (23.0225, 72.5714, "Ahmedabad Site B"),
    "S007": (13.0827, 80.2707, "Chennai Yard"),
    "S008": (26.9124, 75.7873, "Jaipur Site C"),
    "S009": (21.1702, 72.8311, "Surat Depot"),
    "S010": (18.5204, 73.8567, "Pune Site D"),
}


class Simulator:
    """Batch historical telemetry generator for model training and seed data.

    This is **not** the live WebSocket generator (``telemetry_generator.py``).
    Use this class to produce CSV files for training ``AnomalyDetector``,
    ``DemandForecaster``, and ``MaintenanceRiskModel``.

    Parameters
    ----------
    n_assets : int
        Number of equipment assets to simulate.
    n_days : int
        Number of days of history to generate.
    anomaly_rate : float
        Fraction of rows that should contain injected anomalies (0.0–1.0).
    seed : int
        Random seed for reproducibility.
    """

    def __init__(
        self,
        n_assets: int = 50,
        n_days: int = 7,
        anomaly_rate: float = 0.05,
        seed: int = 42,
    ) -> None:
        self.n_assets = n_assets
        self.n_days = n_days
        self.anomaly_rate = anomaly_rate
        self.seed = seed
        self._rng = np.random.default_rng(seed)
        self._py_rng = random.Random(seed)
        self._cost_config = dict(DEFAULT_COST_CONFIG)

    # ── Properties ───────────────────────────────────────────────────────

    @property
    def asset_cost_config(self) -> dict[str, dict[str, float]]:
        """Per-equipment-type cost lookup.

        Returns ``{equipment_type: {rental_rate_per_day, idle_cost_per_hour}}``.
        """
        return dict(self._cost_config)

    # ── Asset setup ──────────────────────────────────────────────────────

    def _build_asset_roster(self) -> list[dict[str, Any]]:
        """Create a roster of assets with fixed metadata."""
        assets = []
        site_ids = list(DEFAULT_SITES.keys())
        for i in range(self.n_assets):
            eq_type = EQUIPMENT_TYPES[i % len(EQUIPMENT_TYPES)]
            # ~10% of assets start unassigned (site_id=None)
            if self._rng.random() < 0.10:
                site_id = None
            else:
                site_id = self._py_rng.choice(site_ids)
            assets.append(
                {
                    "asset_id": f"EQX{1001 + i}",
                    "equipment_type": eq_type,
                    "site_id": site_id,
                    "base_fuel": self._rng.uniform(40, 95),
                    "maintenance_hours": self._rng.uniform(0, 500),
                    "cumulative_engine_hours": self._rng.uniform(100, 2000),
                    "cumulative_idle_hours": self._rng.uniform(10, 400),
                }
            )
        return assets

    # ── Normal telemetry generation ──────────────────────────────────────

    def _generate_normal_row(
        self, asset: dict[str, Any], ts: datetime
    ) -> dict[str, Any]:
        """Generate a single normal (non-anomalous) telemetry row."""
        hour = ts.hour
        is_work_hours = 6 <= hour <= 20 and ts.weekday() < 5

        # Engine is typically active during work hours ONLY if assigned to a site
        engine_active = (
            is_work_hours
            and (asset["site_id"] is not None)
            and self._rng.random() < 0.85
        )

        # Speed: moving during work, 0 otherwise
        if engine_active:
            speed = float(self._rng.uniform(2, 18))
        else:
            speed = 0.0

        # Tilt: small values during normal operation
        tilt = float(self._rng.uniform(0, 15))

        # Fuel: slow drain
        fuel = max(5.0, asset["base_fuel"] - self._rng.uniform(0, 0.05))
        asset["base_fuel"] = fuel

        # GPS: near site centroid with small jitter
        if asset["site_id"] and asset["site_id"] in DEFAULT_SITES:
            clat, clng, _ = DEFAULT_SITES[asset["site_id"]]
            lat = clat + self._rng.normal(0, 0.001)
            lng = clng + self._rng.normal(0, 0.001)
        else:
            lat = 20.0 + self._rng.normal(0, 0.5)
            lng = 78.0 + self._rng.normal(0, 0.5)

        # Cumulative hours (increment by 1 minute = 1/60 hour)
        if engine_active:
            asset["cumulative_engine_hours"] += 1 / 60
            if speed < 0.5:
                asset["cumulative_idle_hours"] += 1 / 60
        asset["maintenance_hours"] += 1 / 60 if engine_active else 0

        return {
            "asset_id": asset["asset_id"],
            "recorded_at": ts.isoformat() + "Z",
            "lat": round(lat, 6),
            "lng": round(lng, 6),
            "engine_hours": round(asset["cumulative_engine_hours"], 2),
            "idle_hours": round(asset["cumulative_idle_hours"], 2),
            "fuel_level_pct": round(fuel, 1),
            "tilt_angle_deg": round(tilt, 1),
            "speed_kmh": round(speed, 1),
            "is_anomaly": False,
            # Internal columns
            "equipment_type": asset["equipment_type"],
            "site_id": asset["site_id"],
            "engine_active": engine_active,
            "hours_since_maintenance": round(asset["maintenance_hours"], 2),
        }

    # ── Anomaly injection ────────────────────────────────────────────────

    def _inject_unauthorized_movement(
        self, row: dict[str, Any], asset: dict[str, Any]
    ) -> dict[str, Any]:
        """Engine active with no assigned site for 30+ min."""
        row["engine_active"] = True
        row["site_id"] = None
        row["speed_kmh"] = round(float(self._rng.uniform(5, 15)), 1)
        # Put GPS far from any site
        row["lat"] = round(25.0 + self._rng.normal(0, 0.5), 6)
        row["lng"] = round(82.0 + self._rng.normal(0, 0.5), 6)
        row["is_anomaly"] = True
        return row

    def _inject_excessive_idle(
        self, row: dict[str, Any], asset: dict[str, Any]
    ) -> dict[str, Any]:
        """Engine active but speed ≈ 0 for 60+ min."""
        row["engine_active"] = True
        row["speed_kmh"] = round(float(self._rng.uniform(0, 0.3)), 1)
        asset["cumulative_idle_hours"] += 1 / 60
        row["idle_hours"] = round(asset["cumulative_idle_hours"], 2)
        row["is_anomaly"] = True
        return row

    def _inject_geofence_breach(
        self, row: dict[str, Any], asset: dict[str, Any]
    ) -> dict[str, Any]:
        """GPS outside site centroid radius."""
        if asset["site_id"] and asset["site_id"] in DEFAULT_SITES:
            clat, clng, _ = DEFAULT_SITES[asset["site_id"]]
            # Push 0.01–0.02 degrees away (~1–2 km)
            direction = self._rng.uniform(0, 2 * math.pi)
            offset = self._rng.uniform(0.01, 0.02)
            row["lat"] = round(clat + offset * math.cos(direction), 6)
            row["lng"] = round(clng + offset * math.sin(direction), 6)
        row["engine_active"] = True
        row["is_anomaly"] = True
        return row

    def _inject_safety_hazard(
        self, row: dict[str, Any], asset: dict[str, Any]
    ) -> dict[str, Any]:
        """Tilt > 30° or speed > 25 km/h in site zone."""
        if self._rng.random() < 0.5:
            # Tilt hazard
            row["tilt_angle_deg"] = round(float(self._rng.uniform(30.5, 50)), 1)
        else:
            # Speed hazard
            row["speed_kmh"] = round(float(self._rng.uniform(26, 45)), 1)
        row["engine_active"] = True
        row["is_anomaly"] = True
        return row

    def _inject_irregular_usage(
        self, row: dict[str, Any], asset: dict[str, Any], ts: datetime
    ) -> dict[str, Any]:
        """Operation outside 06:00–20:00 or on weekends."""
        # Force the timestamp to off-hours
        if ts.weekday() < 5:
            # Shift to late night
            off_hour = self._py_rng.choice([0, 1, 2, 3, 4, 22, 23])
            new_ts = ts.replace(hour=off_hour, minute=self._py_rng.randint(0, 59))
        else:
            new_ts = ts  # Already weekend
        row["recorded_at"] = new_ts.isoformat() + "Z"
        row["engine_active"] = True
        row["speed_kmh"] = round(float(self._rng.uniform(3, 12)), 1)
        row["is_anomaly"] = True
        return row

    def _inject_anomaly(
        self, row: dict[str, Any], asset: dict[str, Any], ts: datetime
    ) -> dict[str, Any]:
        """Randomly pick and inject one anomaly type."""
        anomaly_type = self._py_rng.choice(ANOMALY_TYPES)
        if anomaly_type == "UNAUTHORIZED_MOVEMENT":
            return self._inject_unauthorized_movement(row, asset)
        elif anomaly_type == "EXCESSIVE_IDLE":
            return self._inject_excessive_idle(row, asset)
        elif anomaly_type == "GEOFENCE_BREACH":
            return self._inject_geofence_breach(row, asset)
        elif anomaly_type == "SAFETY_HAZARD":
            return self._inject_safety_hazard(row, asset)
        elif anomaly_type == "IRREGULAR_USAGE":
            return self._inject_irregular_usage(row, asset, ts)
        return row

    # ── Main generation ──────────────────────────────────────────────────

    def generate(self) -> pd.DataFrame:
        """Generate full telemetry DataFrame (DB-ready + internal columns).

        Returns
        -------
        pd.DataFrame
            DataFrame with columns from ``DB_COLUMNS + INTERNAL_COLUMNS``.
        """
        assets = self._build_asset_roster()
        rows: list[dict[str, Any]] = []

        start = datetime(2026, 8, 1, 0, 0, 0)
        total_minutes = self.n_days * 24 * 60

        for asset in assets:
            for minute_offset in range(0, total_minutes, 1):
                # Sample ~every 10 minutes on average to keep row count manageable
                if self._rng.random() > 0.1:
                    continue

                ts = start + timedelta(minutes=minute_offset)
                row = self._generate_normal_row(asset, ts)

                # Inject anomaly with configured probability
                if self._rng.random() < self.anomaly_rate:
                    row = self._inject_anomaly(row, asset, ts)

                rows.append(row)

        df = pd.DataFrame(rows)
        # Ensure column order: DB columns first, then internal
        all_cols = DB_COLUMNS + INTERNAL_COLUMNS
        df = df[[c for c in all_cols if c in df.columns]]
        return df

    def db_ready(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter to only ``telemetry_logs`` DB columns.

        Parameters
        ----------
        df : pd.DataFrame
            Full DataFrame from :meth:`generate`.

        Returns
        -------
        pd.DataFrame
            DataFrame with only the 10 ``telemetry_logs`` columns.
        """
        return df[[c for c in DB_COLUMNS if c in df.columns]].copy()

    def save(self, path: str = "sample_data/telemetry.csv") -> None:
        """Generate and save telemetry to CSV.

        Parameters
        ----------
        path : str
            Output file path.
        """
        df = self.generate()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        df.to_csv(path, index=False)
        print(f"✓ Saved {len(df)} rows to {path}")
        print(f"  Anomaly rate: {df['is_anomaly'].mean():.1%}")
        print(f"  Assets: {df['asset_id'].nunique()}")
        print(f"  Date range: {df['recorded_at'].min()} → {df['recorded_at'].max()}")

    # ── Demand history generator ─────────────────────────────────────────

    def generate_demand_history(
        self, n_sites: int = 10, n_months: int = 6
    ) -> pd.DataFrame:
        """Generate daily equipment demand history for DemandForecaster training.

        Parameters
        ----------
        n_sites : int
            Number of sites.
        n_months : int
            Months of history.

        Returns
        -------
        pd.DataFrame
            Columns: ``date``, ``site_id``, ``equipment_type``, ``units_used``.
        """
        site_ids = [f"S{str(i+1).zfill(3)}" for i in range(n_sites)]
        start_date = datetime(2026, 2, 1).date()
        n_days = n_months * 30

        rows: list[dict[str, Any]] = []
        for site_id in site_ids:
            for eq_type in EQUIPMENT_TYPES:
                base_demand = self._rng.integers(1, 6)
                for day_offset in range(n_days):
                    date = start_date + timedelta(days=day_offset)
                    # Weekly seasonality + trend + noise
                    weekday_factor = 1.0 if date.weekday() < 5 else 0.3
                    trend = day_offset * 0.005
                    noise = self._rng.normal(0, 0.8)
                    demand = max(
                        0,
                        int(
                            round(
                                base_demand * weekday_factor + trend + noise
                            )
                        ),
                    )
                    rows.append(
                        {
                            "date": date.isoformat(),
                            "site_id": site_id,
                            "equipment_type": eq_type,
                            "units_used": demand,
                        }
                    )

        return pd.DataFrame(rows)


# ── CLI entrypoint ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate batch telemetry CSV for ML model training."
    )
    parser.add_argument("--assets", type=int, default=50, help="Number of assets")
    parser.add_argument("--days", type=int, default=7, help="Days of history")
    parser.add_argument(
        "--anomaly-rate", type=float, default=0.05, help="Anomaly injection rate"
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument(
        "--output", default="sample_data/telemetry.csv", help="Output CSV path"
    )
    parser.add_argument(
        "--demand-output",
        default="sample_data/demand_history.csv",
        help="Demand history CSV path",
    )

    args = parser.parse_args()

    sim = Simulator(
        n_assets=args.assets,
        n_days=args.days,
        anomaly_rate=args.anomaly_rate,
        seed=args.seed,
    )

    # Generate telemetry
    sim.save(args.output)

    # Generate demand history
    demand_df = sim.generate_demand_history()
    os.makedirs(os.path.dirname(args.demand_output) or ".", exist_ok=True)
    demand_df.to_csv(args.demand_output, index=False)
    print(f"✓ Saved {len(demand_df)} demand history rows to {args.demand_output}")
