#!/usr/bin/env python3
"""
Generate sample data and evaluate accuracy of all ML components.

Checks:
1. Simulator — data quality, anomaly injection rate
2. AnomalyDetector — precision, recall, F1 against known injected anomalies
3. DemandForecaster — MAPE on holdout set
4. MaintenanceRiskModel — risk tier distribution, score reasonableness
"""

import json
import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import pandas as pd

from ml_engine.simulator import Simulator, DB_COLUMNS, INTERNAL_COLUMNS
from ml_engine.anomaly_detector import AnomalyDetector
from ml_engine.demand_forecaster import DemandForecaster
from ml_engine.maintenance_risk import MaintenanceRiskModel


def separator(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def main():
    # ── 1. Generate sample data ──────────────────────────────────────────
    separator("1. SAMPLE DATA GENERATION")

    sim = Simulator(n_assets=50, n_days=7, anomaly_rate=0.08, seed=42)
    
    t0 = time.time()
    telemetry = sim.generate()
    gen_time = time.time() - t0

    print(f"\n  Generated {len(telemetry):,} telemetry rows in {gen_time:.1f}s")
    print(f"  Assets: {telemetry['asset_id'].nunique()}")
    print(f"  Date range: {telemetry['recorded_at'].min()} → {telemetry['recorded_at'].max()}")
    print(f"  Columns ({len(telemetry.columns)}): {list(telemetry.columns)}")

    # DB-ready check
    db_df = sim.db_ready(telemetry)
    print(f"\n  DB-ready columns ({len(db_df.columns)}): {list(db_df.columns)}")
    assert set(db_df.columns) == set(DB_COLUMNS), "DB column mismatch!"
    print("  ✓ DB schema matches telemetry_logs table")

    # Save to CSV
    sim.save("sample_data/telemetry.csv")

    # Data quality stats
    print(f"\n  ── Data Quality ──")
    print(f"  Null counts:")
    for col in telemetry.columns:
        nulls = telemetry[col].isna().sum()
        if nulls > 0:
            print(f"    {col}: {nulls} nulls ({nulls/len(telemetry):.1%})")
    
    non_null_cols = [c for c in telemetry.columns if telemetry[c].isna().sum() == 0]
    if len(non_null_cols) == len(telemetry.columns):
        print("    No nulls in any column ✓")

    print(f"\n  ── Numeric ranges ──")
    for col in ["engine_hours", "idle_hours", "fuel_level_pct", "tilt_angle_deg", "speed_kmh"]:
        print(f"    {col}: min={telemetry[col].min():.1f}, "
              f"max={telemetry[col].max():.1f}, "
              f"mean={telemetry[col].mean():.1f}")

    # ── 2. Anomaly Detection Accuracy ────────────────────────────────────
    separator("2. ANOMALY DETECTOR ACCURACY")

    # Ground truth: simulator marks is_anomaly=True on injected rows
    ground_truth = telemetry["is_anomaly"].values
    n_true_anomalies = ground_truth.sum()
    true_rate = ground_truth.mean()
    print(f"\n  Ground truth anomalies: {n_true_anomalies} / {len(telemetry)} ({true_rate:.1%})")

    # Build site centroids for geofence
    from ml_engine.simulator import DEFAULT_SITES
    site_centroids = {sid: (lat, lng) for sid, (lat, lng, _) in DEFAULT_SITES.items()}

    detector = AnomalyDetector(tilt_limit=30.0, speed_limit=25.0)
    
    t0 = time.time()
    detector.fit(telemetry, site_centroids=site_centroids)
    fit_time = time.time() - t0
    print(f"  Fit time: {fit_time:.1f}s")

    t0 = time.time()
    anomalies = detector.predict(telemetry)
    pred_time = time.time() - t0
    print(f"  Predict time: {pred_time:.1f}s")
    print(f"  Anomalies detected: {len(anomalies)}")

    # Build prediction set for comparison
    detected_keys = set()
    for a in anomalies:
        detected_keys.add((a["asset_id"], a["detected_at"]))

    predicted = np.zeros(len(telemetry), dtype=bool)
    for i, (_, row) in enumerate(telemetry.iterrows()):
        if (row["asset_id"], row["recorded_at"]) in detected_keys:
            predicted[i] = True

    # Compute precision / recall / F1
    tp = int(np.sum(ground_truth & predicted))
    fp = int(np.sum(~ground_truth & predicted))
    fn = int(np.sum(ground_truth & ~predicted))
    tn = int(np.sum(~ground_truth & ~predicted))

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    print(f"\n  ── Confusion Matrix ──")
    print(f"                 Predicted Normal  Predicted Anomaly")
    print(f"  Actual Normal     {tn:>6}           {fp:>6}")
    print(f"  Actual Anomaly    {fn:>6}           {tp:>6}")

    print(f"\n  ── Metrics ──")
    print(f"  Precision: {precision:.3f}  (of detected anomalies, how many were real)")
    print(f"  Recall:    {recall:.3f}  (of real anomalies, how many were detected)")
    print(f"  F1 Score:  {f1:.3f}")
    print(f"  Accuracy:  {(tp + tn) / len(telemetry):.3f}")

    # Breakdown by anomaly type
    type_counts = {}
    for a in anomalies:
        t = a["anomaly_type"]
        type_counts[t] = type_counts.get(t, 0) + 1

    print(f"\n  ── Detection by Type ──")
    for atype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"    {atype}: {count}")

    # Score distribution
    scores = [a["anomaly_score"] for a in anomalies]
    print(f"\n  ── Anomaly Score Distribution ──")
    print(f"    Min: {min(scores):.2f}, Max: {max(scores):.2f}, Mean: {np.mean(scores):.2f}")
    rule_based = [s for s in scores if s == 1.0]
    ml_based = [s for s in scores if s < 1.0]
    print(f"    Rule-based (score=1.0): {len(rule_based)}")
    print(f"    ML-based (score<1.0):   {len(ml_based)}")

    # Sample output
    print(f"\n  ── Sample Anomaly Output ──")
    print(f"  {json.dumps(anomalies[0], indent=4)}")

    # ── 3. Demand Forecaster Accuracy ────────────────────────────────────
    separator("3. DEMAND FORECASTER ACCURACY")

    demand_data = sim.generate_demand_history(n_sites=10, n_months=6)
    print(f"\n  Training data: {len(demand_data):,} rows")
    print(f"  Sites: {demand_data['site_id'].nunique()}")
    print(f"  Equipment types: {demand_data['equipment_type'].nunique()}")
    print(f"  Date range: {demand_data['date'].min()} → {demand_data['date'].max()}")

    # Hold out last 14 days for evaluation
    demand_data["date"] = pd.to_datetime(demand_data["date"])
    cutoff = demand_data["date"].max() - pd.Timedelta(days=14)
    train = demand_data[demand_data["date"] <= cutoff].copy()
    holdout = demand_data[demand_data["date"] > cutoff].copy()

    print(f"  Train: {len(train):,} rows (up to {cutoff.date()})")
    print(f"  Holdout: {len(holdout):,} rows (last 14 days)")

    forecaster = DemandForecaster(horizon_days=14, min_history_days=30)

    t0 = time.time()
    forecaster.fit(train)
    fit_time = time.time() - t0
    print(f"  Fit time: {fit_time:.1f}s")

    # Evaluate each group
    mapes = []
    maes = []
    group_results = []

    for (site_id, eq_type), group in holdout.groupby(["site_id", "equipment_type"]):
        try:
            forecast = forecaster.predict(site_id, eq_type)
        except KeyError:
            continue

        actual = group.sort_values("date")["units_used"].values[:14]
        predicted_vals = [d["units_needed"] for d in forecast["predicted_demand"][:len(actual)]]

        if len(actual) == 0:
            continue

        actual = np.array(actual, dtype=float)
        predicted_vals = np.array(predicted_vals, dtype=float)

        mae = np.mean(np.abs(actual - predicted_vals))
        # MAPE with protection against zero
        mask = actual > 0
        if mask.any():
            mape = np.mean(np.abs((actual[mask] - predicted_vals[mask]) / actual[mask]))
        else:
            mape = 0.0

        mapes.append(mape)
        maes.append(mae)
        group_results.append({
            "group": f"{site_id}/{eq_type}",
            "mae": mae,
            "mape": mape,
            "confidence": forecast["confidence"],
            "method": forecaster._models.get((site_id, eq_type), {}).get("method", "unknown"),
        })

    print(f"\n  ── Forecast Accuracy (14-day holdout) ──")
    print(f"  Groups evaluated: {len(mapes)}")
    print(f"  Overall MAE:  {np.mean(maes):.2f} units/day")
    print(f"  Overall MAPE: {np.mean(mapes):.1%}")

    # Method breakdown
    arima_groups = [g for g in group_results if g["method"] == "arima"]
    naive_groups = [g for g in group_results if g["method"] == "seasonal_naive"]
    print(f"\n  ARIMA models:         {len(arima_groups)}")
    if arima_groups:
        print(f"    Avg MAE:  {np.mean([g['mae'] for g in arima_groups]):.2f}")
        print(f"    Avg MAPE: {np.mean([g['mape'] for g in arima_groups]):.1%}")
    print(f"  Seasonal naive models: {len(naive_groups)}")
    if naive_groups:
        print(f"    Avg MAE:  {np.mean([g['mae'] for g in naive_groups]):.2f}")
        print(f"    Avg MAPE: {np.mean([g['mape'] for g in naive_groups]):.1%}")

    # Best and worst groups
    group_results.sort(key=lambda x: x["mape"])
    print(f"\n  ── Top 5 Best Forecasts (lowest MAPE) ──")
    for g in group_results[:5]:
        print(f"    {g['group']}: MAE={g['mae']:.2f}, MAPE={g['mape']:.1%}, "
              f"confidence={g['confidence']:.2f}, method={g['method']}")

    print(f"\n  ── Top 5 Worst Forecasts (highest MAPE) ──")
    for g in group_results[-5:]:
        print(f"    {g['group']}: MAE={g['mae']:.2f}, MAPE={g['mape']:.1%}, "
              f"confidence={g['confidence']:.2f}, method={g['method']}")

    # Sample output
    sample_forecast = forecaster.predict("S001", "Excavator")
    print(f"\n  ── Sample Forecast Output ──")
    print(f"  {json.dumps(sample_forecast, indent=4)}")

    # ── 4. Maintenance Risk Model ────────────────────────────────────────
    separator("4. MAINTENANCE RISK MODEL")

    risk_model = MaintenanceRiskModel()
    risk_model.fit(telemetry, anomaly_history=anomalies)
    all_risks = risk_model.predict_all()

    print(f"\n  Assets assessed: {len(all_risks)}")

    # Tier distribution
    tier_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    for r in all_risks:
        tier_counts[r["risk_tier"]] += 1

    print(f"\n  ── Risk Tier Distribution ──")
    for tier in ["HIGH", "MEDIUM", "LOW"]:
        bar = "█" * tier_counts[tier]
        print(f"    {tier:6s}: {tier_counts[tier]:3d}  {bar}")

    # Score distribution
    scores = [r["risk_score"] for r in all_risks]
    print(f"\n  ── Risk Score Distribution ──")
    print(f"    Min: {min(scores):.2f}, Max: {max(scores):.2f}, "
          f"Mean: {np.mean(scores):.2f}, Median: {np.median(scores):.2f}")

    # Failure window distribution
    windows = [r["predicted_failure_window_days"] for r in all_risks]
    print(f"\n  ── Predicted Failure Window ──")
    print(f"    Min: {min(windows)} days, Max: {max(windows)} days, "
          f"Mean: {np.mean(windows):.0f} days")

    # Most common contributing factors
    factor_counts = {}
    for r in all_risks:
        for f in r["contributing_factors"]:
            factor_counts[f] = factor_counts.get(f, 0) + 1

    print(f"\n  ── Contributing Factors (across all assets) ──")
    for f, c in sorted(factor_counts.items(), key=lambda x: -x[1]):
        print(f"    {f}: {c} assets")

    # Compare batch vs live predict
    print(f"\n  ── Batch vs Live Predict Comparison ──")
    test_asset = all_risks[0]["asset_id"]
    batch_result = risk_model.predict(test_asset)
    live_result = risk_model.predict(
        test_asset,
        current_telemetry={
            "engine_hours": 3000.0,
            "idle_hours": 1200.0,
            "hours_since_maintenance": 600.0,
            "tilt_angle_deg": 28.0,
        },
        recent_anomaly_count=15,
    )
    print(f"    {test_asset} batch: score={batch_result['risk_score']:.2f}, "
          f"tier={batch_result['risk_tier']}")
    print(f"    {test_asset} live:  score={live_result['risk_score']:.2f}, "
          f"tier={live_result['risk_tier']}  "
          f"(high engine hrs + anomalies)")

    # Sample output
    high_risk = [r for r in all_risks if r["risk_tier"] == "HIGH"]
    if high_risk:
        print(f"\n  ── Sample HIGH Risk Output ──")
        print(f"  {json.dumps(high_risk[0], indent=4)}")

    # ── Summary ──────────────────────────────────────────────────────────
    separator("SUMMARY")
    print(f"""
  Component               Metric           Value
  ─────────────────────   ───────────────  ────────
  Simulator               Rows generated   {len(telemetry):,}
                          Anomaly rate     {true_rate:.1%}
                          DB columns OK    ✓

  AnomalyDetector         Precision        {precision:.3f}
                          Recall           {recall:.3f}
                          F1 Score         {f1:.3f}
                          Types detected   {len(type_counts)}

  DemandForecaster        MAE              {np.mean(maes):.2f} units/day
                          MAPE             {np.mean(mapes):.1%}
                          ARIMA models     {len(arima_groups)}

  MaintenanceRiskModel    HIGH risk        {tier_counts['HIGH']}
                          MEDIUM risk      {tier_counts['MEDIUM']}
                          LOW risk         {tier_counts['LOW']}
                          Live predict     ✓
""")


if __name__ == "__main__":
    main()
