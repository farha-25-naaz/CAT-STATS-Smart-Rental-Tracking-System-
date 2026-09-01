"""
Integration contract tests — asserts exact JSON keys for all 5 components.

This is the cheapest insurance against integration breakage with Person 2.
Run end-to-end: Simulator → AnomalyDetector → DemandForecaster →
MaintenanceRiskModel → NLSummarizer (mocked).
"""

import json
from unittest.mock import MagicMock

import pytest

from ml_engine.anomaly_detector import AnomalyDetector
from ml_engine.demand_forecaster import DemandForecaster
from ml_engine.maintenance_risk import MaintenanceRiskModel
from ml_engine.nl_summarizer import NLSummarizer
from ml_engine.simulator import DB_COLUMNS, Simulator


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def sim():
    return Simulator(n_assets=10, n_days=3, anomaly_rate=0.10, seed=42)


@pytest.fixture(scope="module")
def telemetry(sim):
    return sim.generate()


@pytest.fixture(scope="module")
def demand_data(sim):
    return sim.generate_demand_history(n_sites=3, n_months=4)


@pytest.fixture(scope="module")
def anomalies(telemetry):
    from ml_engine.simulator import DEFAULT_SITES
    detector = AnomalyDetector(tilt_limit=30.0)
    site_centroids = {sid: (lat, lng) for sid, (lat, lng, _) in DEFAULT_SITES.items()}
    detector.fit(telemetry, site_centroids=site_centroids)
    return detector.predict(telemetry)


@pytest.fixture(scope="module")
def forecasts(demand_data):
    forecaster = DemandForecaster(horizon_days=7, min_history_days=30)
    forecaster.fit(demand_data)
    return forecaster.predict_all()


@pytest.fixture(scope="module")
def risk_assessments(telemetry, anomalies):
    model = MaintenanceRiskModel()
    model.fit(telemetry, anomaly_history=anomalies)
    return model.predict_all()


# ── Contract: telemetry_logs schema ──────────────────────────────────────────

class TestTelemetryLogsContract:
    """Simulator.db_ready() must produce exactly the telemetry_logs columns."""

    EXPECTED_COLUMNS = {
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
    }

    def test_db_ready_exact_columns(self, sim, telemetry):
        db_df = sim.db_ready(telemetry)
        assert set(db_df.columns) == self.EXPECTED_COLUMNS

    def test_no_legacy_columns(self, sim, telemetry):
        db_df = sim.db_ready(telemetry)
        legacy = {"latitude", "longitude", "timestamp", "operator_id"}
        assert legacy.isdisjoint(set(db_df.columns))


# ── Contract: AnomalyDetector output ────────────────────────────────────────

class TestAnomalyContract:
    EXPECTED_KEYS = {
        "asset_id",
        "is_anomaly",
        "anomaly_type",
        "anomaly_score",
        "detected_at",
        "reason",
    }

    def test_anomalies_exist(self, anomalies):
        assert len(anomalies) > 0

    def test_exact_keys(self, anomalies):
        for a in anomalies:
            assert set(a.keys()) == self.EXPECTED_KEYS, (
                f"Anomaly key mismatch: got {set(a.keys())}"
            )

    def test_is_anomaly_always_true(self, anomalies):
        for a in anomalies:
            assert a["is_anomaly"] is True

    def test_serializable(self, anomalies):
        """Must be JSON-serializable for Person 2's API."""
        json.dumps(anomalies)  # Should not raise


# ── Contract: DemandForecaster output ────────────────────────────────────────

class TestForecastContract:
    EXPECTED_KEYS = {
        "site_id",
        "equipment_type",
        "forecast_generated_at",
        "forecast_horizon_days",
        "predicted_demand",
        "confidence",
    }

    EXPECTED_DEMAND_ITEM_KEYS = {"date", "units_needed"}

    def test_forecasts_exist(self, forecasts):
        assert len(forecasts) > 0

    def test_exact_keys(self, forecasts):
        for f in forecasts:
            assert set(f.keys()) == self.EXPECTED_KEYS

    def test_demand_item_keys(self, forecasts):
        for f in forecasts:
            for item in f["predicted_demand"]:
                assert set(item.keys()) == self.EXPECTED_DEMAND_ITEM_KEYS

    def test_serializable(self, forecasts):
        json.dumps(forecasts)


# ── Contract: MaintenanceRiskModel output ────────────────────────────────────

class TestRiskContract:
    EXPECTED_KEYS = {
        "asset_id",
        "risk_score",
        "risk_tier",
        "predicted_failure_window_days",
        "contributing_factors",
    }

    def test_assessments_exist(self, risk_assessments):
        assert len(risk_assessments) > 0

    def test_exact_keys(self, risk_assessments):
        for r in risk_assessments:
            assert set(r.keys()) == self.EXPECTED_KEYS

    def test_risk_tier_valid(self, risk_assessments):
        for r in risk_assessments:
            assert r["risk_tier"] in {"LOW", "MEDIUM", "HIGH"}

    def test_serializable(self, risk_assessments):
        json.dumps(risk_assessments)


# ── Contract: NLSummarizer output (mocked) ───────────────────────────────────

class TestSummarizerContract:
    EXPECTED_KEYS = {"asset_id", "summary", "severity", "generated_at"}

    def test_exact_keys(self, anomalies, risk_assessments, sim):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps({
                    "summary": "Test summary with $210 in fuel costs.",
                    "severity": "HIGH",
                })
            )
        ]
        mock_client.messages.create.return_value = mock_response

        summarizer = NLSummarizer(llm_client=mock_client)
        cost_config = sim.asset_cost_config.get("Excavator", {})

        asset_data = {
            "asset_id": "EQX1001",
            "equipment_type": "Excavator",
            "idle_hours": 8.0,
        }

        result = summarizer.summarize(
            asset_data=asset_data,
            anomaly=anomalies[0] if anomalies else None,
            risk=risk_assessments[0] if risk_assessments else None,
            cost_config=cost_config,
        )

        assert set(result.keys()) == self.EXPECTED_KEYS

    def test_severity_valid(self, sim):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text=json.dumps({"summary": "OK", "severity": "LOW"}))
        ]
        mock_client.messages.create.return_value = mock_response

        summarizer = NLSummarizer(llm_client=mock_client)
        result = summarizer.summarize({"asset_id": "EQX1001"})
        assert result["severity"] in {"LOW", "MEDIUM", "HIGH"}

    def test_serializable(self, sim):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text=json.dumps({"summary": "OK", "severity": "LOW"}))
        ]
        mock_client.messages.create.return_value = mock_response

        summarizer = NLSummarizer(llm_client=mock_client)
        result = summarizer.summarize({"asset_id": "EQX1001"})
        json.dumps(result)
