"""Tests for ml_engine.anomaly_detector."""

import math
import os
import tempfile

import pandas as pd
import pytest

from ml_engine.anomaly_detector import AnomalyDetector, _haversine_m
from ml_engine.simulator import Simulator

# ── Expected output contract keys ────────────────────────────────────────────

EXPECTED_KEYS = {"asset_id", "is_anomaly", "anomaly_type", "anomaly_score", "detected_at", "reason"}

VALID_ANOMALY_TYPES = {
    "UNAUTHORIZED_MOVEMENT",
    "EXCESSIVE_IDLE",
    "GEOFENCE_BREACH",
    "SAFETY_HAZARD",
    "IRREGULAR_USAGE",
}


from ml_engine.simulator import DEFAULT_SITES, Simulator


@pytest.fixture
def sim():
    return Simulator(n_assets=10, n_days=3, anomaly_rate=0.10, seed=42)


@pytest.fixture
def telemetry(sim):
    return sim.generate()


@pytest.fixture
def detector():
    return AnomalyDetector(tilt_limit=30.0, speed_limit=25.0)


@pytest.fixture
def fitted_detector(detector, telemetry):
    site_centroids = {sid: (lat, lng) for sid, (lat, lng, _) in DEFAULT_SITES.items()}
    detector.fit(telemetry, site_centroids=site_centroids)
    return detector


class TestTiltThreshold:
    """Tilt threshold must be 30.0° (aligned with Person 1's frontend)."""

    def test_default_tilt_limit_is_30(self):
        d = AnomalyDetector()
        assert d.tilt_limit == 30.0

    def test_tilt_rule_fires_at_30(self, fitted_detector):
        """A row with tilt=30.5 should trigger SAFETY_HAZARD."""
        row = pd.Series({
            "asset_id": "EQX_TEST",
            "recorded_at": "2026-09-01T12:00:00Z",
            "lat": 28.61,
            "lng": 77.21,
            "engine_hours": 100.0,
            "idle_hours": 10.0,
            "fuel_level_pct": 80.0,
            "tilt_angle_deg": 30.5,  # Just above 30.0
            "speed_kmh": 5.0,
            "is_anomaly": False,
            "equipment_type": "Excavator",
            "site_id": "S001",
            "engine_active": True,
            "hours_since_maintenance": 50.0,
        })
        result = fitted_detector._check_safety_hazard(row)
        assert result is not None
        assert result["anomaly_type"] == "SAFETY_HAZARD"

    def test_tilt_rule_does_not_fire_at_29(self, fitted_detector):
        """A row with tilt=29.0 should NOT trigger SAFETY_HAZARD."""
        row = pd.Series({
            "asset_id": "EQX_TEST",
            "recorded_at": "2026-09-01T12:00:00Z",
            "lat": 28.61,
            "lng": 77.21,
            "tilt_angle_deg": 29.0,
            "speed_kmh": 5.0,
            "site_id": "S001",
            "engine_active": True,
        })
        result = fitted_detector._check_safety_hazard(row)
        assert result is None


class TestUnauthorizedMovement:
    def test_fires_when_engine_on_no_site(self, fitted_detector):
        row = pd.Series({
            "asset_id": "EQX_TEST",
            "recorded_at": "2026-09-01T12:00:00Z",
            "lat": 25.0,
            "lng": 82.0,
            "engine_active": True,
            "site_id": None,
            "tilt_angle_deg": 5.0,
            "speed_kmh": 10.0,
        })
        result = fitted_detector._check_unauthorized_movement(row)
        assert result is not None
        assert result["anomaly_type"] == "UNAUTHORIZED_MOVEMENT"


class TestExcessiveIdle:
    def test_fires_when_engine_on_speed_zero(self, fitted_detector):
        row = pd.Series({
            "asset_id": "EQX_TEST",
            "recorded_at": "2026-09-01T12:00:00Z",
            "lat": 28.61,
            "lng": 77.21,
            "engine_active": True,
            "site_id": "S001",
            "speed_kmh": 0.1,
            "tilt_angle_deg": 2.0,
        })
        result = fitted_detector._check_excessive_idle(row)
        assert result is not None
        assert result["anomaly_type"] == "EXCESSIVE_IDLE"

    def test_does_not_fire_when_speed_normal(self, fitted_detector):
        row = pd.Series({
            "asset_id": "EQX_TEST",
            "recorded_at": "2026-09-01T12:00:00Z",
            "lat": 28.61,
            "lng": 77.21,
            "engine_active": True,
            "site_id": "S001",
            "speed_kmh": 8.5,
            "tilt_angle_deg": 2.0,
        })
        result = fitted_detector._check_excessive_idle(row)
        assert result is None


class TestGeofenceBreach:
    def test_haversine_basic(self):
        """Known distance: ~111 km per degree latitude at equator."""
        dist = _haversine_m(0, 0, 1, 0)
        assert 110_000 < dist < 112_000

    def test_geofence_fires_when_far(self, fitted_detector):
        fitted_detector._site_centroids = {"S001": (28.6, 77.2)}
        row = pd.Series({
            "asset_id": "EQX_TEST",
            "recorded_at": "2026-09-01T12:00:00Z",
            "lat": 29.0,  # Far from centroid
            "lng": 78.0,
            "site_id": "S001",
            "engine_active": True,
            "tilt_angle_deg": 5.0,
            "speed_kmh": 5.0,
        })
        result = fitted_detector._check_geofence_breach(row)
        assert result is not None
        assert result["anomaly_type"] == "GEOFENCE_BREACH"


class TestFitPredict:
    def test_fit_returns_self(self, detector, telemetry):
        result = detector.fit(telemetry)
        assert result is detector

    def test_predict_returns_list(self, fitted_detector, telemetry):
        anomalies = fitted_detector.predict(telemetry)
        assert isinstance(anomalies, list)

    def test_output_keys_match_contract(self, fitted_detector, telemetry):
        anomalies = fitted_detector.predict(telemetry)
        assert len(anomalies) > 0, "Expected at least one anomaly"
        for a in anomalies:
            assert set(a.keys()) == EXPECTED_KEYS, f"Keys mismatch: {set(a.keys())}"

    def test_anomaly_types_are_valid(self, fitted_detector, telemetry):
        anomalies = fitted_detector.predict(telemetry)
        for a in anomalies:
            assert a["anomaly_type"] in VALID_ANOMALY_TYPES

    def test_anomaly_scores_in_range(self, fitted_detector, telemetry):
        anomalies = fitted_detector.predict(telemetry)
        for a in anomalies:
            assert 0.0 <= a["anomaly_score"] <= 1.0


class TestSaveLoad:
    def test_round_trip(self, fitted_detector, telemetry):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "model.joblib")
            fitted_detector.save(path)

            loaded = AnomalyDetector.load(path)
            original = fitted_detector.predict(telemetry)
            reloaded = loaded.predict(telemetry)

            assert len(original) == len(reloaded)
            # Check first few are identical
            for o, r in zip(original[:5], reloaded[:5]):
                assert o["asset_id"] == r["asset_id"]
                assert o["anomaly_type"] == r["anomaly_type"]
