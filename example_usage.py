#!/usr/bin/env python3
"""
Example usage of all 5 ML Engine classes.

Demonstrates the end-to-end flow:
    Simulator → AnomalyDetector → DemandForecaster →
    MaintenanceRiskModel → NLSummarizer (optional, requires ANTHROPIC_API_KEY)
"""

import json
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from ml_engine.simulator import Simulator
from ml_engine.anomaly_detector import AnomalyDetector
from ml_engine.demand_forecaster import DemandForecaster
from ml_engine.maintenance_risk import MaintenanceRiskModel


def main():
    print("=" * 70)
    print("ML Engine — Example Usage")
    print("=" * 70)

    # ── 1. Generate synthetic data ───────────────────────────────────────
    print("\n▸ 1. Generating synthetic telemetry...")
    sim = Simulator(n_assets=10, n_days=3, anomaly_rate=0.08, seed=42)
    telemetry = sim.generate()
    print(f"  Generated {len(telemetry)} telemetry rows")
    print(f"  Columns: {list(telemetry.columns)}")
    print(f"  DB-ready columns: {list(sim.db_ready(telemetry).columns)}")

    # ── 2. Detect anomalies ──────────────────────────────────────────────
    print("\n▸ 2. Running AnomalyDetector (tilt_limit=30.0°)...")
    # Simulate site centroids from Person 2's sites table
    site_centroids = {
        "S001": (28.6139, 77.2090),
        "S002": (19.0760, 72.8777),
        "S003": (12.9716, 77.5946),
        "S004": (22.5726, 88.3639),
        "S005": (17.3850, 78.4867),
        "S006": (23.0225, 72.5714),
        "S007": (13.0827, 80.2707),
        "S008": (26.9124, 75.7873),
        "S009": (21.1702, 72.8311),
        "S010": (18.5204, 73.8567),
    }

    detector = AnomalyDetector(tilt_limit=30.0)
    detector.fit(telemetry, site_centroids=site_centroids)
    anomalies = detector.predict(telemetry)

    print(f"  Detected {len(anomalies)} anomalies")
    if anomalies:
        print(f"  Sample anomaly:")
        print(f"  {json.dumps(anomalies[0], indent=4)}")

    # Save model
    detector.save("models/anomaly_detector.joblib")
    print("  ✓ Model saved to models/anomaly_detector.joblib")

    # ── 3. Forecast demand ───────────────────────────────────────────────
    print("\n▸ 3. Running DemandForecaster...")
    demand_data = sim.generate_demand_history(n_sites=5, n_months=4)
    print(f"  Training on {len(demand_data)} demand history rows")

    forecaster = DemandForecaster(horizon_days=14, min_history_days=30)
    forecaster.fit(demand_data)
    forecast = forecaster.predict("S001", "Excavator")

    print(f"  Forecast for S001/Excavator:")
    print(f"  {json.dumps(forecast, indent=4)}")

    forecaster.save("models/demand_forecaster.joblib")
    print("  ✓ Model saved to models/demand_forecaster.joblib")

    # ── 4. Assess maintenance risk ───────────────────────────────────────
    print("\n▸ 4. Running MaintenanceRiskModel...")
    risk_model = MaintenanceRiskModel()
    risk_model.fit(telemetry, anomaly_history=anomalies)

    # Batch predict (uses training-time snapshot — for development/testing)
    risk = risk_model.predict("EQX1001")
    print(f"  Risk (batch mode) for EQX1001:")
    print(f"  {json.dumps(risk, indent=4)}")

    # Live predict (uses current telemetry — for production API calls)
    live_risk = risk_model.predict(
        "EQX1001",
        current_telemetry={
            "engine_hours": 1800.5,
            "idle_hours": 420.0,
            "hours_since_maintenance": 350.0,
            "tilt_angle_deg": 22.0,
        },
        recent_anomaly_count=7,
    )
    print(f"\n  Risk (live mode) for EQX1001:")
    print(f"  {json.dumps(live_risk, indent=4)}")

    risk_model.save("models/maintenance_risk.joblib")
    print("  ✓ Model saved to models/maintenance_risk.joblib")

    # ── 5. NL Summary (requires ANTHROPIC_API_KEY) ───────────────────────
    print("\n▸ 5. NLSummarizer...")
    if os.environ.get("ANTHROPIC_API_KEY"):
        from ml_engine.nl_summarizer import NLSummarizer

        summarizer = NLSummarizer()
        cost_config = sim.asset_cost_config.get("Excavator", {})
        summary = summarizer.summarize(
            asset_data={
                "asset_id": "EQX1001",
                "equipment_type": "Excavator",
                "idle_hours": 8.0,
                "site_id": "S001",
            },
            anomaly=anomalies[0] if anomalies else None,
            risk=risk,
            cost_config=cost_config,
        )
        print(f"  Summary:")
        print(f"  {json.dumps(summary, indent=4)}")
    else:
        print("  ⚠ Skipped — set ANTHROPIC_API_KEY to enable NL summaries")
        print("  Example output:")
        print('  {')
        print('    "asset_id": "EQX1005",')
        print('    "summary": "Bulldozer EQX1005 has been idling for 8 hours '
              'at Site S006, burning an estimated $210 in fuel.",')
        print('    "severity": "HIGH",')
        print('    "generated_at": "2026-09-01T12:00:03Z"')
        print('  }')

    print("\n" + "=" * 70)
    print("✓ All components working. Ready for Person 2 integration.")
    print("=" * 70)


if __name__ == "__main__":
    main()
