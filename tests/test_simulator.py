"""Tests for ml_engine.simulator."""

import pandas as pd
import pytest

from ml_engine.simulator import DB_COLUMNS, INTERNAL_COLUMNS, Simulator


@pytest.fixture
def sim():
    """Small simulator for fast tests."""
    return Simulator(n_assets=5, n_days=2, anomaly_rate=0.05, seed=42)


@pytest.fixture
def telemetry(sim):
    return sim.generate()


class TestSimulatorColumns:
    """Verify output schema matches Person 2's telemetry_logs table."""

    def test_has_all_db_columns(self, telemetry):
        for col in DB_COLUMNS:
            assert col in telemetry.columns, f"Missing DB column: {col}"

    def test_has_all_internal_columns(self, telemetry):
        for col in INTERNAL_COLUMNS:
            assert col in telemetry.columns, f"Missing internal column: {col}"

    def test_no_latitude_column(self, telemetry):
        """Old column name should NOT exist."""
        assert "latitude" not in telemetry.columns

    def test_no_longitude_column(self, telemetry):
        assert "longitude" not in telemetry.columns

    def test_no_timestamp_column(self, telemetry):
        assert "timestamp" not in telemetry.columns

    def test_no_operator_id_column(self, telemetry):
        assert "operator_id" not in telemetry.columns


class TestDbReady:
    """Verify db_ready() returns exactly the telemetry_logs columns."""

    def test_db_ready_columns(self, sim, telemetry):
        db_df = sim.db_ready(telemetry)
        assert set(db_df.columns) == set(DB_COLUMNS)

    def test_db_ready_excludes_internal(self, sim, telemetry):
        db_df = sim.db_ready(telemetry)
        for col in INTERNAL_COLUMNS:
            assert col not in db_df.columns

    def test_db_ready_row_count_unchanged(self, sim, telemetry):
        db_df = sim.db_ready(telemetry)
        assert len(db_df) == len(telemetry)


class TestAnomalyInjection:
    """Verify anomaly injection works and rate is reasonable."""

    def test_has_anomalies(self, telemetry):
        assert telemetry["is_anomaly"].any()

    def test_anomaly_rate_within_tolerance(self, telemetry):
        rate = telemetry["is_anomaly"].mean()
        # Allow wide tolerance due to randomness
        assert 0.01 <= rate <= 0.20, f"Anomaly rate {rate:.2%} out of range"

    def test_zero_anomaly_rate(self):
        sim = Simulator(n_assets=3, n_days=1, anomaly_rate=0.0, seed=42)
        df = sim.generate()
        assert not df["is_anomaly"].any()


class TestColumnTypes:
    """Verify column data types."""

    def test_asset_id_is_string(self, telemetry):
        assert telemetry["asset_id"].dtype == object

    def test_engine_hours_is_numeric(self, telemetry):
        assert pd.api.types.is_numeric_dtype(telemetry["engine_hours"])

    def test_idle_hours_is_numeric(self, telemetry):
        assert pd.api.types.is_numeric_dtype(telemetry["idle_hours"])

    def test_is_anomaly_is_bool(self, telemetry):
        assert telemetry["is_anomaly"].dtype == bool


class TestCostConfig:
    """Verify asset_cost_config."""

    def test_has_all_equipment_types(self, sim):
        config = sim.asset_cost_config
        for eq_type in ["Excavator", "Crane", "Loader", "Dump Truck", "Bulldozer"]:
            assert eq_type in config

    def test_has_required_keys(self, sim):
        config = sim.asset_cost_config
        for eq_type, costs in config.items():
            assert "rental_rate_per_day" in costs
            assert "idle_cost_per_hour" in costs

    def test_values_are_positive(self, sim):
        for eq_type, costs in sim.asset_cost_config.items():
            assert costs["rental_rate_per_day"] > 0
            assert costs["idle_cost_per_hour"] > 0


class TestDemandHistory:
    """Verify generate_demand_history()."""

    def test_output_columns(self, sim):
        df = sim.generate_demand_history(n_sites=3, n_months=2)
        expected = {"date", "site_id", "equipment_type", "units_used"}
        assert set(df.columns) == expected

    def test_output_has_data(self, sim):
        df = sim.generate_demand_history(n_sites=3, n_months=2)
        assert len(df) > 0

    def test_units_non_negative(self, sim):
        df = sim.generate_demand_history(n_sites=3, n_months=2)
        assert (df["units_used"] >= 0).all()
