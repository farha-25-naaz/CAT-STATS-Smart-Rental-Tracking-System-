# CAT‑STATS — Smart Rental Tracking System

Real‑time fleet‑intelligence platform for rented construction equipment:
live telemetry on a map, QR‑driven check‑in/out, anomaly & safety lockouts,
ARIMA demand forecasting, maintenance‑risk scoring, and LLM alert summaries.

The repo is one full stack:

| Layer | Path | Stack |
|---|---|---|
| **Frontend** | `frontend/` | React 19, Vite 8, Tailwind v4, Leaflet, Chart.js, `html5-qrcode` |
| **Backend API** | `backend/` | FastAPI, Supabase (Postgres), APScheduler, WebSockets |
| **ML library** | `ml_engine/` | scikit‑learn, statsmodels (ARIMA), Groq/Anthropic LLM |

The frontend is **fully live** — no mock data. It reads every screen from the
backend and streams updates over a WebSocket.

---

## 1. Architecture

```
                 ┌────────────────────────────┐
                 │  React SPA  (Vite :5173)    │
                 │  fleet · radar · forecast · │
                 │  safety · QR codes          │
                 └───────┬────────────┬────────┘
              REST /api  │            │  WS /ws/live
                         ▼            ▼
                 ┌────────────────────────────┐
                 │  FastAPI  (uvicorn :8000)  │
                 │  routes + WebSocket hub    │
                 │  ml_orchestration (models) │
                 └───────┬────────────┬────────┘
              Supabase   │            │  imports
              (Postgres) ▼            ▼
                 ┌──────────────┐  ┌──────────────────┐
                 │ assets/sites │  │ ml_engine/*.py   │
                 │ telemetry_*  │  │ AnomalyDetector  │
                 │ alerts       │  │ DemandForecaster │
                 │ maintenance_ │  │ MaintenanceRisk  │
                 │ risk / supervisors │ NLSummarizer  │
                 └──────────────┘  └──────────────────┘
```

- ML models are trained once from simulated data and cached as
  `ml_engine/models/*.joblib`; the backend loads them at startup.
- A background scheduler flips overdue rentals to `OVERDUE` every 60 s and
  refreshes geofence centroids every 15 min.

---

## 2. Prerequisites

- **Python 3.11+** (3.12 tested)
- **Node.js 20+** (24 tested)
- A **Supabase** project with the schema applied (assets, sites,
  telemetry_logs, alerts, maintenance_risk, summaries, supervisors).
- Optional: a **Groq API key** for natural‑language alert summaries.

---

## 3. Backend setup (`backend/`)

### 3.1 Environment

Create `backend/.env`:

```ini
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_KEY=<service-role-or-anon-key>
GROQ_API_KEY=<optional – enables NL summaries>
# Optional: lock CORS to the frontend origin (default "*")
CORS_ALLOW_ORIGINS=http://localhost:5173
```

### 3.2 Install & seed

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python seed_demo_data.py     # 10 assets, 4 sites, ~125 telemetry rows, 2 alerts
python seed_supervisors.py   # SUP-001/1234, SUP-002/4321, SUP-003/0000
```

`seed_demo_data.py` is idempotent — safe to re‑run to reset the demo.

### 3.3 Run

```bash
python -m uvicorn main:app --reload --port 8000
```

Health check: <http://localhost:8000/health> →
`{"status":"ok","db_connected":true,"active_websocket_connections":0}`
Interactive API docs: <http://localhost:8000/docs>

> First boot trains the ML models if `ml_engine/models/*.joblib` are missing
> (~30–60 s). Pre‑build them with `python ml_orchestration.py` from `backend/`.

---

## 4. Frontend setup (`frontend/`)

```bash
cd frontend
cp .env.example .env          # VITE_API_BASE_URL, VITE_WS_URL
npm install
npm run dev                   # http://localhost:5173
```

`.env`:

```ini
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws/live
```

Production build: `npm run build` → `dist/` (preview with `npm run preview`).

> Open the app via **`http://localhost:5173`**, not a LAN IP — browsers block
> camera access (QR scanning) outside `localhost`/HTTPS.

---

## 5. Demo script

1. Start backend, then frontend. Dashboard loads the live fleet.
2. **Rented Assets** — table of all 10 machines; click a row → jumps to the
   map and auto‑centres on that asset.
3. **Live Site Radar** — Leaflet map, markers move on a 2 s loop, trails,
   geofence rings, click a marker for the telemetry drawer.
4. **Demand Forecast** — ARIMA curve from `/forecast`; the AI briefing card
   calls `/assets/{id}/generate-summary` (needs `GROQ_API_KEY`, else a
   graceful fallback line).
5. **Asset QR Codes** — printable sheet of one QR per asset (encodes the bare
   `asset_id`). Print it or show on screen.
6. **Scan Asset QR Tag** (sidebar) — opens the check‑in/out modal:
   - *Scan with Camera* (uses the native `BarcodeDetector` when available), or
   - *Enter asset code* `EXC-101` (no‑camera fallback), or
   - pick from the dropdown.
   - The modal auto‑selects **Check‑Out** for an `UNASSIGNED` asset and
     **Check‑In** for one that's already out, and blocks the invalid direction.
7. **Trigger a safety lockout** (separate terminal):

   ```bash
   curl -X POST localhost:8000/demo/replay \
     -H "content-type: application/json" \
     -d "{\"scenario\":\"safety_breach\",\"asset_id\":\"CRN-201\"}"
   ```

   Within ~2 s the WebSocket pushes `SAFETY_LOCKOUT`; the asset goes red and
   the lockout modal opens. Clear it with **SUP-001 / 1234**.

### Seeded data

| Assets | Sites | Supervisors |
|---|---|---|
| `EXC-101/102` Excavator | `S001` Whitefield Yard | `SUP-001` / `1234` |
| `CRN-201/202` Crane | `S002` Electronic City Site | `SUP-002` / `4321` |
| `BLD-301/302` Bulldozer | `S003` Hebbal Depot | `SUP-003` / `0000` |
| `LDR-401/402` Loader | `S004` Peenya Industrial | |
| `DMP-501/502` Dump Truck | | |

`LDR-402` and `DMP-502` start `UNASSIGNED` (available to check out).

---

## 6. API reference

Base URL `http://localhost:8000`. Full schema at `/docs`.

### Fleet & reference data

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | liveness + DB reachability + WS connection count |
| `GET` | `/assets/live` | every asset joined with its latest telemetry, latest unresolved alert, maintenance‑risk tier, site name, rates |
| `GET` | `/sites` | rental sites with geofence centroid + radius |
| `GET` | `/operators` | distinct operator IDs currently assigned |
| `GET` | `/usage-summary?asset_id&days` | per‑day engine/idle deltas + avg fuel |

### Check‑in / check‑out

| Method | Path | Body |
|---|---|---|
| `POST` | `/check-out` | `{asset_id, site_id, operator_id, check_in_date}` — asset must be `UNASSIGNED` |
| `POST` | `/check-in` | `{asset_id}` — resolves any open `OVERDUE` alert |

### ML

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/forecast?site_id&equipment_type&horizon` | ARIMA demand forecast (horizon 1–90, default 14) |
| `GET` | `/assets/{id}/risk` | score maintenance risk from latest telemetry + anomaly history, persist it |
| `POST` | `/assets/{id}/generate-summary` | LLM alert summary (503 if no `GROQ_API_KEY`) |

### Safety

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/safety/override` | `{asset_id, supervisor_id, pin, resolution_note, resume_status}` — clears a `SAFETY_LOCKOUT` (409 if the asset isn't locked, 401 on bad PIN) |
| `GET` | `/api/v1/safety/active-lockouts` | assets currently in `SAFETY_LOCKOUT` + their critical alert |

### Live feed & ingest

| Method | Path | Purpose |
|---|---|---|
| `WS` | `/ws/live` | broadcasts `{event: …}` frames: `TELEMETRY`, `SAFETY_LOCKOUT`, `LOCKOUT_CLEARED`, `DEMO_REPLAY_START/END` |
| `POST` | `/ingest/telemetry` | telemetry row + server‑side geofence check |
| `POST` | `/ingest/anomaly` | raises an alert; `SAFETY_HAZARD` ⇒ `SAFETY_LOCKOUT` + broadcast |
| `POST` | `/ingest/risk` | upsert `maintenance_risk` |
| `POST` | `/ingest/summary` | attach summary to latest alert (or `summaries` table) |
| `POST` | `/demo/replay` | `{scenario:"safety_breach", asset_id}` — scripted lockout through the real pipeline |

---

## 7. Data & status model

**Asset status** (`assets.status`): `ACTIVE`, `IDLE`, `OVERDUE`,
`UNASSIGNED`, `SAFETY_LOCKOUT`.

The frontend maps these to three display buckets:
`ACTIVE → ACTIVE`, `SAFETY_LOCKOUT`/anomaly `→ CRITICAL_ALERT`,
everything else `→ IDLE_WARNING`. The raw value is kept as `rawStatus` and
drives the check‑in/out direction gating.

**`telemetry_logs`**

| Column | Type | Notes |
|---|---|---|
| `asset_id` | str | e.g. `EXC-101` |
| `recorded_at` | datetime | event timestamp |
| `lat`, `lng` | float | GPS |
| `engine_hours`, `idle_hours` | float | cumulative; carried forward if absent |
| `fuel_level_pct` | float | 0–100 |
| `tilt_angle_deg` | float | > 30° ⇒ safety hazard |
| `speed_kmh` | float | ground speed |
| `is_anomaly` | bool | set by the ML layer |

**Anomaly types:** `UNAUTHORIZED_MOVEMENT`, `EXCESSIVE_IDLE`,
`GEOFENCE_BREACH`, `SAFETY_HAZARD`, `IRREGULAR_USAGE`.

**Risk tiers:** `LOW` (< 0.4), `MEDIUM` (0.4–0.7), `HIGH` (≥ 0.7).

### Key thresholds

| Parameter | Value |
|---|---|
| Tilt safety limit | 30.0° |
| Speed limit (site zone) | 25.0 km/h |
| Geofence radius | per‑site (450–600 m seeded) |
| Idle threshold | 60 min |
| Unauthorized‑movement window | 45 min |

---

## 8. ML library (`ml_engine/`)

Standalone, importable, no backend dependency.

| Class | File | Purpose |
|---|---|---|
| `Simulator` | `simulator.py` | historical telemetry + demand history generator |
| `AnomalyDetector` | `anomaly_detector.py` | rule engine + IsolationForest |
| `DemandForecaster` | `demand_forecaster.py` | per‑`(site, equipment_type)` ARIMA, seasonal‑naive fallback |
| `MaintenanceRiskModel` | `maintenance_risk.py` | weighted risk score per asset |
| `NLSummarizer` | `nl_summarizer.py` | LLM alert summaries (Anthropic Messages API surface; backend adapts Groq to it) |

```bash
# from repo root
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m ml_engine.simulator      # sample_data/telemetry.csv
python -m pytest tests/ -v
python example_usage.py
```

### Example

```python
from ml_engine import AnomalyDetector, DemandForecaster, MaintenanceRiskModel, Simulator

sim = Simulator(n_assets=50, n_days=7)
telemetry = sim.generate()

detector = AnomalyDetector(tilt_limit=30.0)
detector.fit(telemetry, site_centroids={"S001": (28.6, 77.2)})
anomalies = detector.predict(telemetry)

forecaster = DemandForecaster(horizon_days=14)
forecaster.fit(sim.generate_demand_history())
forecast = forecaster.predict("S001", "Excavator")

risk_model = MaintenanceRiskModel()
risk_model.fit(telemetry, anomaly_history=anomalies)
risk = risk_model.predict("EXC-101")
```

### JSON contracts

<details><summary>AnomalyDetector / DemandForecaster / MaintenanceRiskModel / NLSummarizer</summary>

```json
// AnomalyDetector
{"asset_id":"EXC-101","is_anomaly":true,"anomaly_type":"UNAUTHORIZED_MOVEMENT",
 "anomaly_score":0.87,"detected_at":"2026-09-01T12:00:03Z",
 "reason":"Engine active with no assigned site for 45 minutes"}

// DemandForecaster
{"site_id":"S003","equipment_type":"Excavator","forecast_generated_at":"2026-09-01T00:00:00Z",
 "forecast_horizon_days":14,
 "predicted_demand":[{"date":"2026-09-02","units_needed":3}],"confidence":0.78}

// MaintenanceRiskModel
{"asset_id":"EXC-101","risk_score":0.72,"risk_tier":"HIGH",
 "predicted_failure_window_days":5,
 "contributing_factors":["high_runtime_hours","excessive_idle_ratio"]}

// NLSummarizer
{"asset_id":"DMP-501","summary":"Dump Truck DMP-501 has idled 8 h at S004, ~$210 fuel.",
 "severity":"HIGH","generated_at":"2026-09-01T12:00:03Z"}
```
</details>

---

## 9. Frontend structure (`frontend/src/`)

| Path | Role |
|---|---|
| `api/client.js` | `fetch` wrapper, `ApiError`, base‑URL/WS‑URL resolution |
| `api/endpoints.js` | one function per backend route |
| `api/normalize.js` | backend → UI shape (snake→camel, status buckets, `lat/lng`→`coords`, WS frame merge) |
| `hooks/useFleet.js` | initial `/sites` + `/assets/live` load, normalize, polling, `refetch` |
| `hooks/useLiveSocket.js` | `/ws/live` with backoff reconnect; patches assets by id, fires lockout callbacks |
| `components/FleetDashboard.jsx` | KPI cards + machinery table |
| `components/LiveFlightMap.jsx` | Leaflet radar; auto‑flies to `selectedAsset` |
| `components/AnalyticsAndForecast.jsx` | usage bars + ARIMA line + AI briefing |
| `components/CheckInOutModal.jsx` | QR scan / manual code / dropdown → `/check-out` `/check-in`, direction gating |
| `components/QrScanner.jsx` | camera QR reader (native `BarcodeDetector`, StrictMode‑safe) |
| `components/AssetQrSheet.jsx` | printable QR sheet (one per asset) |
| `components/SafetyLockoutModal.jsx` | supervisor PIN → `/api/v1/safety/override` |

---

## 10. Troubleshooting

| Symptom | Fix |
|---|---|
| Frontend red banner "Cannot reach backend" | start the backend on :8000, then hit **Retry** |
| Port 8000 in use (Windows) | `powershell "Get-NetTCPConnection -LocalPort 8000 -State Listen \| %{ Stop-Process -Id $_.OwningProcess -Force }"` |
| Camera won't open / blank | use `http://localhost:5173`; allow the camera prompt; close other apps holding the webcam |
| QR not recognised | print the sheet (screen‑to‑webcam glares); use Chrome/Edge; or type the code in **Enter asset code** |
| AI briefing card shows fallback text | set `GROQ_API_KEY` in `backend/.env` |
| Lockout modal says "not in a lockout state" (409) | that asset isn't `SAFETY_LOCKOUT`; run `/demo/replay` first, or just close the dialog |
| First backend boot is slow | it's training ML models; pre‑build with `python ml_orchestration.py` |

---

## 11. Repo layout

```
.
├── backend/            FastAPI app
│   ├── main.py            app + /assets/live + /check-in/out + /ws/live
│   ├── ml_routes.py       /assets/{id}/risk, /generate-summary
│   ├── forecast_routes.py /forecast
│   ├── catalog_routes.py  /sites, /operators
│   ├── safety_routes.py   /api/v1/safety/*
│   ├── ingest_routes.py   /ingest/*
│   ├── demo_routes.py     /health, /demo/replay
│   ├── ml_orchestration.py model load/train + Groq shim
│   ├── seed_demo_data.py / seed_supervisors.py
│   └── .env               (not committed)
├── frontend/           React + Vite SPA
│   ├── src/               see §9
│   └── .env / .env.example
├── ml_engine/          standalone ML library + models/
├── tests/              pytest suite for ml_engine
├── sample_data/        generated telemetry CSV
└── example_usage.py    end-to-end ml_engine demo
```
