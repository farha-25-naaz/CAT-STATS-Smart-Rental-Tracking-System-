# ML Engine — Construction Equipment Fleet Intelligence

> Anomaly detection, demand forecasting, maintenance risk scoring, and NL summaries for construction equipment fleets.

## Quick Start

```bash
# Set up environment
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Generate sample data
python -m ml_engine.simulator

# Run tests
python -m pytest tests/ -v

# Run full example
python example_usage.py
```

## Full-stack demo (backend API + React frontend)

**1. Backend** (`backend/`, needs `backend/.env` with `SUPABASE_URL`, `SUPABASE_KEY`, optional `GROQ_API_KEY`):

```bash
cd backend
pip install -r requirements.txt
python seed_demo_data.py       # assets, sites, telemetry, alerts
python seed_supervisors.py     # demo supervisor PINs (SUP-001 / 1234)
python -m uvicorn main:app --reload --port 8000
```

**2. Frontend** (`frontend/`):

```bash
cd frontend
cp .env.example .env           # points at http://localhost:8000
npm install
npm run dev                    # http://localhost:5173
```

The frontend is fully live — it reads `/assets/live`, `/sites`, `/forecast`,
`/usage-summary`, streams `/ws/live`, and drives check-in/out and the safety
override against the real API. Trigger a lockout for the demo with:

```bash
curl -X POST localhost:8000/demo/replay -H 'content-type: application/json' \
  -d '{"scenario":"safety_breach","asset_id":"CRN-202"}'
```

## Components

| Class | File | Purpose |
|---|---|---|
| `Simulator` | `ml_engine/simulator.py` | Batch historical telemetry generator (CSV) |
| `AnomalyDetector` | `ml_engine/anomaly_detector.py` | Rule engine + IsolationForest anomaly detection |
| `DemandForecaster` | `ml_engine/demand_forecaster.py` | Per-site ARIMA demand forecasting |
| `MaintenanceRiskModel` | `ml_engine/maintenance_risk.py` | Weighted risk scoring per asset |
| `NLSummarizer` | `ml_engine/nl_summarizer.py` | LLM-powered natural language alert summaries |

## Telemetry Schema (Person 2 Integration)

The `Simulator.db_ready()` method outputs exactly the columns in Person 2's `telemetry_logs` table:

| Column | Type | Description |
|---|---|---|
| `asset_id` | str | Equipment ID, e.g. `EQX1001` |
| `recorded_at` | datetime | Event timestamp |
| `lat` | float | GPS latitude |
| `lng` | float | GPS longitude |
| `engine_hours` | float | Cumulative engine runtime hours |
| `idle_hours` | float | Cumulative idle hours |
| `fuel_level_pct` | float | Fuel level 0–100 |
| `tilt_angle_deg` | float | Equipment tilt angle |
| `speed_kmh` | float | Ground speed |
| `is_anomaly` | bool | Set by AnomalyDetector |

> **Note**: `telemetry_generator.py` (live WebSocket, 1-2s interval) is a separate file and NOT part of this module.

## JSON Contracts

### AnomalyDetector Output

```json
{
  "asset_id": "EQX1001",
  "is_anomaly": true,
  "anomaly_type": "UNAUTHORIZED_MOVEMENT",
  "anomaly_score": 0.87,
  "detected_at": "2026-09-01T12:00:03Z",
  "reason": "Engine active with no assigned site (site_id=NULL) for 45 minutes"
}
```

**Anomaly types**: `UNAUTHORIZED_MOVEMENT`, `EXCESSIVE_IDLE`, `GEOFENCE_BREACH`, `SAFETY_HAZARD`, `IRREGULAR_USAGE`

### DemandForecaster Output

```json
{
  "site_id": "S003",
  "equipment_type": "Excavator",
  "forecast_generated_at": "2026-09-01T00:00:00Z",
  "forecast_horizon_days": 14,
  "predicted_demand": [
    {"date": "2026-09-02", "units_needed": 3},
    {"date": "2026-09-03", "units_needed": 4}
  ],
  "confidence": 0.78
}
```

### MaintenanceRiskModel Output

```json
{
  "asset_id": "EQX1001",
  "risk_score": 0.72,
  "risk_tier": "HIGH",
  "predicted_failure_window_days": 5,
  "contributing_factors": ["high_runtime_hours", "excessive_idle_ratio"]
}
```

**Risk tiers**: `LOW` (< 0.4), `MEDIUM` (0.4–0.7), `HIGH` (≥ 0.7)

### NLSummarizer Output

```json
{
  "asset_id": "EQX1005",
  "summary": "Bulldozer EQX1005 has been idling for 8 hours at Site S006, burning an estimated $210 in fuel.",
  "severity": "HIGH",
  "generated_at": "2026-09-01T12:00:03Z"
}
```

Requires `ANTHROPIC_API_KEY` environment variable.

## Usage

```python
from ml_engine import (
    AnomalyDetector,
    DemandForecaster,
    MaintenanceRiskModel,
    NLSummarizer,
    Simulator,
)

# Generate data
sim = Simulator(n_assets=50, n_days=7)
telemetry = sim.generate()

# Detect anomalies
detector = AnomalyDetector(tilt_limit=30.0)
detector.fit(telemetry, site_centroids={"S001": (28.6, 77.2)})
anomalies = detector.predict(telemetry)

# Forecast demand
demand = sim.generate_demand_history()
forecaster = DemandForecaster(horizon_days=14)
forecaster.fit(demand)
forecast = forecaster.predict("S001", "Excavator")

# Assess maintenance risk
risk_model = MaintenanceRiskModel()
risk_model.fit(telemetry, anomaly_history=anomalies)
risk = risk_model.predict("EQX1001")

# Generate NL summary (requires API key)
summarizer = NLSummarizer()
summary = summarizer.summarize(
    asset_data={"asset_id": "EQX1001", "equipment_type": "Excavator", "idle_hours": 8},
    anomaly=anomalies[0],
    risk=risk,
    cost_config=sim.asset_cost_config["Excavator"],
)

# Save/load models
detector.save("models/anomaly_detector.joblib")
loaded = AnomalyDetector.load("models/anomaly_detector.joblib")
```

## Key Thresholds

| Parameter | Value | Aligned with |
|---|---|---|
| Tilt safety limit | **30.0°** | Person 1 frontend lockout, telemetry_generator.py |
| Speed limit (site zone) | 25.0 km/h | Site safety rules |
| Geofence radius | 500m | Person 2's `sites` table |
| Idle threshold | 60 min | Fleet policy |
| Unauthorized movement window | 45 min | Fleet policy |
