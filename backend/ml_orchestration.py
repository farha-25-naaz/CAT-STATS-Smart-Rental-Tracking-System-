"""Phase 5 — wire the read-only ``ml_engine`` library into the FastAPI backend.

Responsibilities
----------------
* Load trained models from ``ml_engine/models/*.joblib`` (or train + save them
  once from simulated data if any are missing).
* Expose the loaded instances as module-level singletons for the route layer.
* Build / refresh the ``{site_id: (center_lat, center_lng)}`` lookup from the
  live ``sites`` table and feed it to ``AnomalyDetector``.

Nothing in ``ml_engine/`` is modified — it is imported as a library.
Run ``python ml_orchestration.py`` from the ``backend/`` dir to pre-build the
model files before starting uvicorn (otherwise the first boot trains inline).
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

# ml_engine uses absolute imports rooted at the repo root ("import ml_engine.*"),
# but uvicorn is launched from backend/, so the repo root is not on sys.path.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ml_engine.anomaly_detector import AnomalyDetector  # noqa: E402
from ml_engine.demand_forecaster import DemandForecaster  # noqa: E402
from ml_engine.maintenance_risk import MaintenanceRiskModel  # noqa: E402
from ml_engine.nl_summarizer import NLSummarizer  # noqa: E402
from ml_engine.simulator import DEFAULT_COST_CONFIG, DEFAULT_SITES, Simulator  # noqa: E402

from db import supabase  # noqa: E402

MODELS_DIR = _REPO_ROOT / "ml_engine" / "models"
_ANOMALY_PATH = MODELS_DIR / "anomaly_detector.joblib"
_DEMAND_PATH = MODELS_DIR / "demand_forecaster.joblib"
_RISK_PATH = MODELS_DIR / "maintenance_risk.joblib"

# ── Module-level singletons (populated by load_or_train_models()) ─────────────
anomaly_detector: AnomalyDetector | None = None
demand_forecaster: DemandForecaster | None = None
maintenance_risk_model: MaintenanceRiskModel | None = None
nl_summarizer: NLSummarizer | None = None
site_centroids: dict[str, tuple[float, float]] = {}


_DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"


# ── Groq → Anthropic client shim ───────────────────────────────────────────
# ml_engine.NLSummarizer is read-only and speaks the Anthropic Messages API
# (client.messages.create(...) -> resp.content[0].text). Its constructor takes
# an injectable llm_client, so we adapt Groq's OpenAI-style chat.completions to
# that exact surface without touching ml_engine/.

class _GroqMessagesAdapter:
    def __init__(self, groq_client, model: str) -> None:
        self._groq = groq_client
        self._model = model

    def create(self, model=None, max_tokens=256, messages=None, **_):
        # gpt-oss / qwen on Groq are reasoning models: reasoning tokens count
        # against max_tokens and can starve `content`. Give headroom, keep
        # reasoning short, and force a JSON body.
        kwargs = {
            "model": self._model,
            "max_tokens": max(max_tokens, 1024),
            "messages": messages or [],
        }
        try:
            resp = self._groq.chat.completions.create(
                **kwargs,
                reasoning_effort="low",
                response_format={"type": "json_object"},
            )
        except Exception:  # noqa: BLE001 - model without these knobs: retry plain
            resp = self._groq.chat.completions.create(**kwargs)

        msg = resp.choices[0].message
        text = (msg.content or "").strip()
        if not text:
            # Some reasoning models leave content empty; salvage a JSON object
            # from the reasoning trace so NLSummarizer's parser still works.
            reasoning = getattr(msg, "reasoning", "") or ""
            start, end = reasoning.find("{"), reasoning.rfind("}")
            text = reasoning[start : end + 1] if 0 <= start < end else reasoning
        return SimpleNamespace(content=[SimpleNamespace(text=text)])


class _GroqClientShim:
    def __init__(self, api_key: str, model: str) -> None:
        from groq import Groq

        self.messages = _GroqMessagesAdapter(Groq(api_key=api_key), model)


def _build_summarizer() -> NLSummarizer:
    """NLSummarizer backed by Groq if GROQ_API_KEY is set, else the default
    (Anthropic) client, else a client-less instance that 503s on use."""
    groq_key = os.environ.get("GROQ_API_KEY") or os.environ.get("Groq_API_KEY")
    if groq_key:
        model = os.environ.get("GROQ_MODEL", _DEFAULT_GROQ_MODEL)
        try:
            summ = NLSummarizer(llm_client=_GroqClientShim(groq_key, model), model=model)
            print(f"[ml] NLSummarizer using Groq ({model})")
            return summ
        except Exception as exc:  # noqa: BLE001 - fall through to default
            print(f"[ml] Groq client init failed ({exc}); falling back")

    summ = NLSummarizer()
    if summ._client is None:
        print(
            "[ml] NLSummarizer has no LLM client "
            "(set GROQ_API_KEY in backend/.env); "
            "/assets/{id}/generate-summary will return 503 until then"
        )
    return summ


# ── Site centroid lookup ────────────────────────────────────────────────────

def get_site_centroids() -> dict[str, tuple[float, float]]:
    """Return ``{site_id: (center_lat, center_lng)}`` from the live sites table.

    Falls back to the simulator's built-in ``DEFAULT_SITES`` when the table is
    empty or unreachable, so the geofence rule always has reference points.
    """
    try:
        rows = (
            supabase.table("sites")
            .select("site_id,center_lat,center_lng")
            .execute()
            .data
        ) or []
    except Exception as exc:  # noqa: BLE001 - keep startup alive
        print(f"[ml] get_site_centroids query failed: {exc}")
        rows = []

    centroids: dict[str, tuple[float, float]] = {}
    for r in rows:
        lat, lng = r.get("center_lat"), r.get("center_lng")
        if lat is not None and lng is not None:
            centroids[r["site_id"]] = (float(lat), float(lng))

    if not centroids:
        centroids = {sid: (lat, lng) for sid, (lat, lng, _name) in DEFAULT_SITES.items()}
        print(f"[ml] sites table empty — using {len(centroids)} DEFAULT_SITES centroids")

    return centroids


def refresh_site_centroids() -> dict[str, tuple[float, float]]:
    """Re-fetch site centroids and push them into the live AnomalyDetector.

    Wired to the existing APScheduler in main.py so a rare site edit propagates
    without a server restart. Re-assigns the detector's centroid table directly
    (no re-fit — the IsolationForest is unaffected by centroids).
    """
    global site_centroids
    site_centroids = get_site_centroids()
    if anomaly_detector is not None:
        anomaly_detector._site_centroids = site_centroids
    print(f"[ml] site centroids refreshed ({len(site_centroids)} sites)")
    return site_centroids


# ── Model load / train ──────────────────────────────────────────────────────

def _train_and_save() -> tuple[AnomalyDetector, DemandForecaster, MaintenanceRiskModel]:
    """Generate synthetic data, fit the three trainable models, persist them."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    print("[ml] training models from simulated data (one-time)...")

    sim = Simulator(n_assets=30, n_days=7, anomaly_rate=0.08, seed=42)
    telemetry = sim.generate()

    centroids = get_site_centroids()

    t0 = time.time()
    detector = AnomalyDetector(tilt_limit=30.0)
    detector.fit(telemetry, site_centroids=centroids)
    detector.save(str(_ANOMALY_PATH))
    print(f"[ml]   AnomalyDetector fitted in {time.time() - t0:.1f}s -> {_ANOMALY_PATH.name}")

    t0 = time.time()
    anomalies = detector.predict(telemetry)
    risk_model = MaintenanceRiskModel()
    risk_model.fit(telemetry, anomaly_history=anomalies)
    risk_model.save(str(_RISK_PATH))
    print(f"[ml]   MaintenanceRiskModel fitted in {time.time() - t0:.1f}s -> {_RISK_PATH.name}")

    t0 = time.time()
    demand_data = sim.generate_demand_history(n_sites=10, n_months=4)
    forecaster = DemandForecaster(horizon_days=14, min_history_days=30)
    forecaster.fit(demand_data)
    forecaster.save(str(_DEMAND_PATH))
    print(f"[ml]   DemandForecaster fitted in {time.time() - t0:.1f}s -> {_DEMAND_PATH.name}")

    return detector, forecaster, risk_model


def load_or_train_models() -> None:
    """Populate the module singletons.

    Loads every ``*.joblib`` that exists; if any of the three trainable models
    is missing, trains + saves all three from simulated data. ``NLSummarizer``
    needs no training (thin Claude API wrapper) and is always instantiated.
    """
    global anomaly_detector, demand_forecaster, maintenance_risk_model
    global nl_summarizer, site_centroids

    have_all = _ANOMALY_PATH.exists() and _DEMAND_PATH.exists() and _RISK_PATH.exists()

    if have_all:
        try:
            anomaly_detector = AnomalyDetector.load(str(_ANOMALY_PATH))
            demand_forecaster = DemandForecaster.load(str(_DEMAND_PATH))
            maintenance_risk_model = MaintenanceRiskModel.load(str(_RISK_PATH))
            print("[ml] loaded models from ml_engine/models/*.joblib")
        except Exception as exc:  # noqa: BLE001 - corrupt file -> retrain
            print(f"[ml] load failed ({exc}); retraining")
            have_all = False

    if not have_all:
        anomaly_detector, demand_forecaster, maintenance_risk_model = _train_and_save()

    # Keep the geofence rule pointed at live site coordinates.
    site_centroids = get_site_centroids()
    anomaly_detector._site_centroids = site_centroids

    nl_summarizer = _build_summarizer()


# ── Accessors (route layer imports these, not the raw globals) ───────────────

def get_anomaly_detector() -> AnomalyDetector:
    if anomaly_detector is None:
        raise RuntimeError("Models not loaded — load_or_train_models() must run at startup")
    return anomaly_detector


def get_demand_forecaster() -> DemandForecaster:
    if demand_forecaster is None:
        raise RuntimeError("Models not loaded — load_or_train_models() must run at startup")
    return demand_forecaster


def get_maintenance_risk_model() -> MaintenanceRiskModel:
    if maintenance_risk_model is None:
        raise RuntimeError("Models not loaded — load_or_train_models() must run at startup")
    return maintenance_risk_model


def get_nl_summarizer() -> NLSummarizer:
    if nl_summarizer is None:
        raise RuntimeError("Models not loaded — load_or_train_models() must run at startup")
    return nl_summarizer


def cost_config_for_asset(asset: dict) -> dict[str, float]:
    """Resolve ``{rental_rate_per_day, idle_cost_per_hour}`` for an asset.

    Prefers the per-asset columns on the ``assets`` row (real rental terms);
    falls back to the simulator's per-equipment-type ``DEFAULT_COST_CONFIG``
    only for whichever value is missing/NULL.
    """
    defaults = DEFAULT_COST_CONFIG.get(asset.get("type") or "", {})
    out: dict[str, float] = {}
    for key in ("rental_rate_per_day", "idle_cost_per_hour"):
        val = asset.get(key)
        if val is None:
            val = defaults.get(key)
        if val is not None:
            out[key] = float(val)
    return out


if __name__ == "__main__":
    load_or_train_models()
    print("[ml] done — model files ready in", MODELS_DIR)
