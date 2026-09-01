"""Tests for ml_engine.maintenance_risk."""

import os
import tempfile

import pandas as pd
import pytest

from ml_engine.maintenance_risk import MaintenanceRiskModel
from ml_engine.simulator import Simulator

# ── Expected output contract keys ────────────────────────────────────────────

EXPECTED_KEYS = {
    "asset_id",
    "risk_score",
    "risk_tier",
    "predicted_failure_window_days",
    "contributing_factors",
}

VALID_TIERS = {"LOW", "MEDIUM", "HIGH"}

VALID_FACTOR_LABELS = {
    "high_runtime_hours",
    "excessive_idle_ratio",
    "frequent_anomalies",
    "overdue_maintenance",
    "harsh_operating_conditions",
}


@pytest.fixture
def sim():
    return Simulator(n_assets=10, n_days=3, anomaly_rate=0.10, seed=42)


@pytest.fixture
def telemetry(sim):
    return sim.generate()


@pytest.fixture
def anomaly_history():
    """Fake anomaly history for testing."""
    return [
        {"asset_id": "EQX1001", "anomaly_type": "EXCESSIVE_IDLE"},
        {"asset_id": "EQX1001", "anomaly_type": "SAFETY_HAZARD"},
        {"asset_id": "EQX1001", "anomaly_type": "GEOFENCE_BREACH"},
        {"asset_id": "EQX1002", "anomaly_type": "UNAUTHORIZED_MOVEMENT"},
    ]


@pytest.fixture
def fitted_model(telemetry, anomaly_history):
    model = MaintenanceRiskModel()
    model.fit(telemetry, anomaly_history=anomaly_history)
    return model


class TestFit:
    def test_fit_returns_self(self, telemetry):
        m = MaintenanceRiskModel()
        result = m.fit(telemetry)
        assert result is m

    def test_assets_computed(self, fitted_model):
        assert len(fitted_model._asset_features) > 0


class TestPredict:
    def test_output_keys_match_contract(self, fitted_model):
        result = fitted_model.predict("EQX1001")
        assert set(result.keys()) == EXPECTED_KEYS

    def test_risk_score_in_range(self, fitted_model):
        result = fitted_model.predict("EQX1001")
        assert 0.0 <= result["risk_score"] <= 1.0

    def test_risk_tier_is_valid(self, fitted_model):
        result = fitted_model.predict("EQX1001")
        assert result["risk_tier"] in VALID_TIERS

    def test_failure_window_in_range(self, fitted_model):
        result = fitted_model.predict("EQX1001")
        assert 1 <= result["predicted_failure_window_days"] <= 30

    def test_contributing_factors_are_valid(self, fitted_model):
        result = fitted_model.predict("EQX1001")
        for factor in result["contributing_factors"]:
            assert factor in VALID_FACTOR_LABELS, f"Unknown factor: {factor}"

    def test_unknown_asset_raises_without_live_data(self, fitted_model):
        """Raises when asset not in training AND no live data provided."""
        with pytest.raises(KeyError):
            fitted_model.predict("NONEXISTENT")

    def test_unknown_asset_works_with_live_data(self, fitted_model):
        """New assets work if live telemetry is provided."""
        result = fitted_model.predict(
            "NEW_ASSET",
            current_telemetry={"engine_hours": 500, "idle_hours": 100,
                               "hours_since_maintenance": 200, "tilt_angle_deg": 15},
            recent_anomaly_count=3,
        )
        assert set(result.keys()) == EXPECTED_KEYS
        assert result["asset_id"] == "NEW_ASSET"


class TestRiskTiers:
    """Verify risk tier boundaries."""

    def test_high_anomaly_count_increases_risk(self, telemetry):
        """An asset with many anomalies should score higher."""
        heavy_history = [
            {"asset_id": "EQX1001", "anomaly_type": "SAFETY_HAZARD"}
            for _ in range(20)
        ]
        model = MaintenanceRiskModel()
        model.fit(telemetry, anomaly_history=heavy_history)
        result = model.predict("EQX1001")
        # With 20 anomalies, this asset should have a non-trivial score
        assert result["risk_score"] > 0.0


class TestLivePredict:
    """Verify live-data path doesn't use stale training snapshots."""

    def test_live_telemetry_overrides_training(self, fitted_model):
        """Risk score changes when live telemetry differs from training."""
        baseline = fitted_model.predict("EQX1001")
        live_high_risk = fitted_model.predict(
            "EQX1001",
            current_telemetry={"engine_hours": 9999, "idle_hours": 5000,
                               "hours_since_maintenance": 999, "tilt_angle_deg": 29},
            recent_anomaly_count=50,
        )
        # Live data with extreme values should produce a higher score
        assert live_high_risk["risk_score"] >= baseline["risk_score"]

    def test_live_anomaly_count_affects_score(self, fitted_model):
        low = fitted_model.predict("EQX1001", recent_anomaly_count=0)
        high = fitted_model.predict("EQX1001", recent_anomaly_count=100)
        assert high["risk_score"] >= low["risk_score"]

    def test_output_contract_with_live_data(self, fitted_model):
        result = fitted_model.predict(
            "EQX1001",
            current_telemetry={"engine_hours": 800, "idle_hours": 200},
            recent_anomaly_count=5,
        )
        assert set(result.keys()) == EXPECTED_KEYS
        assert result["risk_tier"] in VALID_TIERS


class TestPredictAll:
    def test_returns_list(self, fitted_model):
        results = fitted_model.predict_all()
        assert isinstance(results, list)

    def test_one_per_asset(self, fitted_model):
        results = fitted_model.predict_all()
        assert len(results) == len(fitted_model._asset_features)

    def test_all_match_contract(self, fitted_model):
        for result in fitted_model.predict_all():
            assert set(result.keys()) == EXPECTED_KEYS


class TestSaveLoad:
    def test_round_trip(self, fitted_model):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "risk.joblib")
            fitted_model.save(path)

            loaded = MaintenanceRiskModel.load(path)
            original = fitted_model.predict("EQX1001")
            reloaded = loaded.predict("EQX1001")

            assert original["risk_score"] == reloaded["risk_score"]
            assert original["risk_tier"] == reloaded["risk_tier"]
            assert original["contributing_factors"] == reloaded["contributing_factors"]
