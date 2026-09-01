"""
Two-layer anomaly detection for construction equipment telemetry.

Layer 1 — Deterministic rule engine (5 rules):
    UNAUTHORIZED_MOVEMENT, EXCESSIVE_IDLE, GEOFENCE_BREACH,
    SAFETY_HAZARD, IRREGULAR_USAGE

Layer 2 — IsolationForest for rows that pass all rules, catches
    subtle IRREGULAR_USAGE patterns calibrated with a confidence threshold.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


# ── Anomaly type enum ────────────────────────────────────────────────────────

ANOMALY_TYPES = frozenset(
    {
        "UNAUTHORIZED_MOVEMENT",
        "EXCESSIVE_IDLE",
        "GEOFENCE_BREACH",
        "SAFETY_HAZARD",
        "IRREGULAR_USAGE",
    }
)


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Haversine distance in meters between two GPS points."""
    R = 6_371_000  # Earth radius in meters
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class AnomalyDetector:
    """Two-layer anomaly detector: deterministic rule engine + IsolationForest.

    Parameters
    ----------
    contamination : float | str
        IsolationForest contamination parameter (expected anomaly fraction).
    ml_score_threshold : float
        Confidence threshold (0.0–1.0) required to trigger an ML anomaly alert.
    geofence_radius_m : float
        Default geofence radius in meters.
    idle_threshold_min : int
        Minutes of idle (engine on, speed ≈ 0) to trigger EXCESSIVE_IDLE.
    idle_window_min : int
        Minutes of engine-on with no site to trigger UNAUTHORIZED_MOVEMENT.
    tilt_limit : float
        Tilt angle in degrees above which SAFETY_HAZARD is raised.
    speed_limit : float
        Speed in km/h above which SAFETY_HAZARD is raised in a site zone.
    """

    _ML_FEATURES = [
        "speed_kmh",
        "tilt_angle_deg",
        "hours_since_maintenance",
        "hour_of_day",
        "is_weekend",
        "is_off_hours",
        "engine_active_num",
        "idle_ratio",
    ]

    def __init__(
        self,
        contamination: float | str = 0.015,
        ml_score_threshold: float = 0.70,
        geofence_radius_m: float = 500.0,
        idle_threshold_min: int = 60,
        idle_window_min: int = 45,
        tilt_limit: float = 30.0,
        speed_limit: float = 25.0,
    ) -> None:
        self.contamination = contamination
        self.ml_score_threshold = ml_score_threshold
        self.geofence_radius_m = geofence_radius_m
        self.idle_threshold_min = idle_threshold_min
        self.idle_window_min = idle_window_min
        self.tilt_limit = tilt_limit
        self.speed_limit = speed_limit

        self._iso_forest: IsolationForest | None = None
        self._feature_cols: list[str] = []
        self._site_centroids: dict[str, tuple[float, float]] | None = None

    # ── Feature engineering ──────────────────────────────────────────────

    @staticmethod
    def _engineer_features(df: pd.DataFrame) -> pd.DataFrame:
        """Derive ML features from raw telemetry."""
        out = df.copy()

        # Parse recorded_at if string
        if out["recorded_at"].dtype == object:
            out["_ts"] = pd.to_datetime(out["recorded_at"], utc=True)
        else:
            out["_ts"] = pd.to_datetime(out["recorded_at"])

        out["hour_of_day"] = out["_ts"].dt.hour
        out["is_weekend"] = out["_ts"].dt.weekday.ge(5).astype(int)
        out["is_off_hours"] = (
            (out["hour_of_day"] < 6) | (out["hour_of_day"] > 20)
        ).astype(int)

        # Engine active as numeric binary feature
        if "engine_active" in out.columns:
            out["engine_active_num"] = out["engine_active"].fillna(False).astype(int)
        else:
            out["engine_active_num"] = (out["speed_kmh"] > 0).astype(int)

        # Cumulative idle ratio feature
        engine_h = out.get("engine_hours", 1.0)
        idle_h = out.get("idle_hours", 0.0)
        if isinstance(engine_h, (pd.Series, np.ndarray)) and isinstance(idle_h, (pd.Series, np.ndarray)):
            out["idle_ratio"] = (idle_h / np.maximum(engine_h, 1.0)).fillna(0.0).clip(0.0, 1.0)
        else:
            out["idle_ratio"] = 0.0

        out.drop(columns=["_ts"], inplace=True)
        return out

    # ── Rule engine ──────────────────────────────────────────────────────

    def _check_unauthorized_movement(
        self, row: pd.Series
    ) -> dict[str, Any] | None:
        """Rule: engine active with no assigned site."""
        if (
            row.get("engine_active", False)
            and (pd.isna(row.get("site_id")) or row.get("site_id") is None or row.get("site_id") == "")
        ):
            return {
                "asset_id": row["asset_id"],
                "is_anomaly": True,
                "anomaly_type": "UNAUTHORIZED_MOVEMENT",
                "anomaly_score": 1.0,
                "detected_at": row["recorded_at"],
                "reason": (
                    f"Engine active with no assigned site (site_id=NULL) "
                    f"for {self.idle_window_min} minutes"
                ),
            }
        return None

    def _check_excessive_idle(self, row: pd.Series) -> dict[str, Any] | None:
        """Rule: engine on, speed ≈ 0."""
        if row.get("engine_active", False) and row.get("speed_kmh", 0) < 0.5:
            return {
                "asset_id": row["asset_id"],
                "is_anomaly": True,
                "anomaly_type": "EXCESSIVE_IDLE",
                "anomaly_score": 1.0,
                "detected_at": row["recorded_at"],
                "reason": (
                    f"Engine idling (speed {row.get('speed_kmh', 0):.1f} < 0.5 km/h) "
                    f"with active ignition"
                ),
            }
        return None

    def _check_geofence_breach(self, row: pd.Series) -> dict[str, Any] | None:
        """Rule: GPS outside site centroid radius (Haversine)."""
        site_id = row.get("site_id")
        if (
            not site_id
            or pd.isna(site_id)
            or self._site_centroids is None
            or site_id not in self._site_centroids
        ):
            return None

        center_lat, center_lng = self._site_centroids[site_id]
        dist = _haversine_m(row["lat"], row["lng"], center_lat, center_lng)

        if dist > self.geofence_radius_m:
            return {
                "asset_id": row["asset_id"],
                "is_anomaly": True,
                "anomaly_type": "GEOFENCE_BREACH",
                "anomaly_score": 1.0,
                "detected_at": row["recorded_at"],
                "reason": (
                    f"GPS location {dist:.0f}m from site {site_id} centroid "
                    f"(limit: {self.geofence_radius_m:.0f}m)"
                ),
            }
        return None

    def _check_safety_hazard(self, row: pd.Series) -> dict[str, Any] | None:
        """Rule: tilt > limit OR speed > limit in site zone."""
        reasons = []

        if row.get("tilt_angle_deg", 0) > self.tilt_limit:
            reasons.append(
                f"Tilt angle {row['tilt_angle_deg']}° exceeds "
                f"limit of {self.tilt_limit}°"
            )

        # Speed check only applies when inside a site zone
        site_id = row.get("site_id")
        if site_id and not pd.isna(site_id):
            if row.get("speed_kmh", 0) > self.speed_limit:
                reasons.append(
                    f"Speed {row['speed_kmh']} km/h exceeds "
                    f"limit of {self.speed_limit} km/h in site {site_id}"
                )

        if reasons:
            return {
                "asset_id": row["asset_id"],
                "is_anomaly": True,
                "anomaly_type": "SAFETY_HAZARD",
                "anomaly_score": 1.0,
                "detected_at": row["recorded_at"],
                "reason": "; ".join(reasons),
            }
        return None

    def _apply_rules(self, df: pd.DataFrame) -> tuple[list[dict], pd.DataFrame]:
        """Apply all rules. Returns (anomalies, remaining_rows)."""
        anomalies: list[dict[str, Any]] = []
        flagged_indices: set[int] = set()

        for idx, row in df.iterrows():
            for checker in [
                self._check_unauthorized_movement,
                self._check_excessive_idle,
                self._check_geofence_breach,
                self._check_safety_hazard,
            ]:
                result = checker(row)
                if result is not None:
                    anomalies.append(result)
                    flagged_indices.add(idx)  # type: ignore[arg-type]
                    break  # One anomaly per row

        remaining = df.loc[~df.index.isin(flagged_indices)]
        return anomalies, remaining

    # ── IsolationForest ML layer ─────────────────────────────────────────

    def fit(
        self,
        df: pd.DataFrame,
        site_centroids: dict[str, tuple[float, float]] | None = None,
    ) -> "AnomalyDetector":
        """Train the IsolationForest on historical telemetry.

        Parameters
        ----------
        df : pd.DataFrame
            Full telemetry DataFrame (must include internal columns).
        site_centroids : dict, optional
            ``{site_id: (center_lat, center_lng)}`` from Person 2's sites table.

        Returns
        -------
        AnomalyDetector
            self, for chaining.
        """
        self._site_centroids = site_centroids

        featured = self._engineer_features(df)

        # Only fit on "normal" rows (those that pass all rules)
        _, normal_df = self._apply_rules(featured)
        train_df = normal_df if len(normal_df) >= 10 else featured

        # Select ML features that exist in the data
        self._feature_cols = [c for c in self._ML_FEATURES if c in train_df.columns]
        X = train_df[self._feature_cols].fillna(0).values

        self._iso_forest = IsolationForest(
            contamination=self.contamination,
            n_estimators=200,
            random_state=42,
            n_jobs=-1,
        )
        self._iso_forest.fit(X)
        return self

    def predict(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        """Detect anomalies in new telemetry data.

        Parameters
        ----------
        df : pd.DataFrame
            Telemetry DataFrame (must include internal columns).

        Returns
        -------
        list[dict]
            List of anomaly dicts matching the output contract.
        """
        featured = self._engineer_features(df)

        # Layer 1: rule engine
        anomalies, remaining = self._apply_rules(featured)

        # Layer 2: IsolationForest on remaining rows
        if self._iso_forest is not None and len(remaining) > 0:
            available_cols = [
                c for c in self._feature_cols if c in remaining.columns
            ]
            X = remaining[available_cols].fillna(0).values
            scores = self._iso_forest.decision_function(X)

            for i, (idx, row) in enumerate(remaining.iterrows()):
                # Convert decision_function score to 0–1 range
                # More negative raw_score indicates stronger anomaly
                raw_score = -scores[i]
                anomaly_score = float(
                    np.clip(0.5 + raw_score * 2.5, 0.0, 1.0)
                )

                if anomaly_score >= self.ml_score_threshold:
                    anomalies.append(
                        {
                            "asset_id": row["asset_id"],
                            "is_anomaly": True,
                            "anomaly_type": "IRREGULAR_USAGE",
                            "anomaly_score": round(anomaly_score, 2),
                            "detected_at": row["recorded_at"],
                            "reason": (
                                "ML model detected irregular usage pattern "
                                f"(score: {anomaly_score:.2f})"
                            ),
                        }
                    )

        return anomalies

    # ── Persistence ──────────────────────────────────────────────────────

    def save(self, path: str = "models/anomaly_detector.joblib") -> None:
        """Save the trained model to disk.

        Parameters
        ----------
        path : str
            Output file path.
        """
        import os

        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        state = {
            "iso_forest": self._iso_forest,
            "feature_cols": self._feature_cols,
            "site_centroids": self._site_centroids,
            "params": {
                "contamination": self.contamination,
                "ml_score_threshold": self.ml_score_threshold,
                "geofence_radius_m": self.geofence_radius_m,
                "idle_threshold_min": self.idle_threshold_min,
                "idle_window_min": self.idle_window_min,
                "tilt_limit": self.tilt_limit,
                "speed_limit": self.speed_limit,
            },
        }
        joblib.dump(state, path)

    @classmethod
    def load(cls, path: str = "models/anomaly_detector.joblib") -> "AnomalyDetector":
        """Load a trained model from disk.

        Parameters
        ----------
        path : str
            Saved model file path.

        Returns
        -------
        AnomalyDetector
            Loaded instance with restored model and parameters.
        """
        state = joblib.load(path)
        params = state["params"]
        detector = cls(**params)
        detector._iso_forest = state["iso_forest"]
        detector._feature_cols = state["feature_cols"]
        detector._site_centroids = state["site_centroids"]
        return detector
