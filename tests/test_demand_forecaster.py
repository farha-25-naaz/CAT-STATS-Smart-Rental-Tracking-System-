"""Tests for ml_engine.demand_forecaster."""

import os
import tempfile

import pandas as pd
import pytest

from ml_engine.demand_forecaster import DemandForecaster
from ml_engine.simulator import Simulator

# ── Expected output contract keys ────────────────────────────────────────────

EXPECTED_KEYS = {
    "site_id",
    "equipment_type",
    "forecast_generated_at",
    "forecast_horizon_days",
    "predicted_demand",
    "confidence",
}

EXPECTED_DEMAND_ITEM_KEYS = {"date", "units_needed"}


@pytest.fixture
def demand_data():
    sim = Simulator(seed=42)
    return sim.generate_demand_history(n_sites=3, n_months=4)


@pytest.fixture
def fitted_forecaster(demand_data):
    forecaster = DemandForecaster(horizon_days=7, min_history_days=30)
    forecaster.fit(demand_data)
    return forecaster


class TestFit:
    def test_fit_returns_self(self, demand_data):
        f = DemandForecaster()
        result = f.fit(demand_data)
        assert result is f

    def test_models_created_for_all_groups(self, fitted_forecaster, demand_data):
        groups = demand_data.groupby(["site_id", "equipment_type"]).ngroups
        assert len(fitted_forecaster._models) == groups


class TestPredict:
    def test_predict_returns_dict(self, fitted_forecaster):
        result = fitted_forecaster.predict("S001", "Excavator")
        assert isinstance(result, dict)

    def test_output_keys_match_contract(self, fitted_forecaster):
        result = fitted_forecaster.predict("S001", "Excavator")
        assert set(result.keys()) == EXPECTED_KEYS

    def test_predicted_demand_structure(self, fitted_forecaster):
        result = fitted_forecaster.predict("S001", "Excavator")
        assert isinstance(result["predicted_demand"], list)
        assert len(result["predicted_demand"]) == 7  # horizon_days

        for item in result["predicted_demand"]:
            assert set(item.keys()) == EXPECTED_DEMAND_ITEM_KEYS
            assert isinstance(item["units_needed"], int)
            assert item["units_needed"] >= 0

    def test_confidence_in_range(self, fitted_forecaster):
        result = fitted_forecaster.predict("S001", "Excavator")
        assert 0.0 <= result["confidence"] <= 1.0

    def test_unknown_group_raises(self, fitted_forecaster):
        with pytest.raises(KeyError):
            fitted_forecaster.predict("UNKNOWN_SITE", "Excavator")


class TestPredictAll:
    def test_returns_list(self, fitted_forecaster):
        results = fitted_forecaster.predict_all()
        assert isinstance(results, list)

    def test_one_per_group(self, fitted_forecaster):
        results = fitted_forecaster.predict_all()
        assert len(results) == len(fitted_forecaster._models)

    def test_all_match_contract(self, fitted_forecaster):
        for result in fitted_forecaster.predict_all():
            assert set(result.keys()) == EXPECTED_KEYS


class TestFallback:
    def test_short_series_uses_naive(self):
        """Series < min_history_days should fall back to seasonal naive."""
        # Create very short series (15 days)
        dates = pd.date_range("2026-01-01", periods=15)
        df = pd.DataFrame({
            "date": [d.strftime("%Y-%m-%d") for d in dates],
            "site_id": "S001",
            "equipment_type": "Crane",
            "units_used": [3, 4, 3, 4, 5, 1, 0] * 2 + [3],
        })
        f = DemandForecaster(horizon_days=7, min_history_days=30)
        f.fit(df)
        assert f._models[("S001", "Crane")]["method"] == "seasonal_naive"

        result = f.predict("S001", "Crane")
        assert set(result.keys()) == EXPECTED_KEYS


class TestSaveLoad:
    def test_round_trip(self, fitted_forecaster):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "forecaster.joblib")
            fitted_forecaster.save(path)

            loaded = DemandForecaster.load(path)
            original = fitted_forecaster.predict("S001", "Excavator")
            reloaded = loaded.predict("S001", "Excavator")

            assert original["site_id"] == reloaded["site_id"]
            assert original["confidence"] == reloaded["confidence"]
            assert len(original["predicted_demand"]) == len(reloaded["predicted_demand"])
