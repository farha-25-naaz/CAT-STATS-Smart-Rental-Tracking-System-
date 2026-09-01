"""
Weighted rule-based maintenance risk scoring for construction equipment.

Computes a 0–1 risk score per asset based on runtime hours, idle ratio,
anomaly history, maintenance overdue hours, and operating severity.
Assigns risk tiers (LOW / MEDIUM / HIGH) and lists contributing factors.

MVP uses a deterministic weighted formula — a trained ML model is deferred
to post-MVP.
"""

from __future__ import annotations

import os
from typing import Any

import joblib
import numpy as np
import pandas as pd


# ── Default weights ──────────────────────────────────────────────────────────

DEFAULT_WEIGHTS: dict[str, float] = {
    "total_engine_hours": 0.30,
    "idle_ratio": 0.20,
    "anomaly_count_30d": 0.25,
    "hours_since_maintenance": 0.15,
    "avg_tilt_severity": 0.10,
}

# Readable labels for contributing_factors output
FACTOR_LABELS: dict[str, str] = {
    "total_engine_hours": "high_runtime_hours",
    "idle_ratio": "excessive_idle_ratio",
    "anomaly_count_30d": "frequent_anomalies",
    "hours_since_maintenance": "overdue_maintenance",
    "avg_tilt_severity": "harsh_operating_conditions",
}

TILT_LIMIT = 30.0  # Matches AnomalyDetector threshold


class MaintenanceRiskModel:
    """Weighted rule-based maintenance risk scorer.

    Parameters
    ----------
    weights : dict, optional
        Custom feature weights. Defaults to ``DEFAULT_WEIGHTS``.
    """

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self.weights = dict(weights or DEFAULT_WEIGHTS)
        self._asset_features: dict[str, dict[str, float]] = {}
        self._feature_ranges: dict[str, tuple[float, float]] = {}
        self._fitted = False

    # ── Feature computation ──────────────────────────────────────────────

    @staticmethod
    def _compute_asset_features(
        df: pd.DataFrame,
        anomaly_history: list[dict[str, Any]] | None = None,
    ) -> dict[str, dict[str, float]]:
        """Compute per-asset features from telemetry + anomaly history.

        Returns ``{asset_id: {feature_name: value}}``.
        """
        features: dict[str, dict[str, float]] = {}

        for asset_id, group in df.groupby("asset_id"):
            # Total engine hours: use max cumulative value
            total_engine_hours = float(
                group["engine_hours"].max() if "engine_hours" in group.columns else 0
            )

            # Idle ratio
            total_idle = float(
                group["idle_hours"].max() if "idle_hours" in group.columns else 0
            )
            idle_ratio = (
                total_idle / total_engine_hours if total_engine_hours > 0 else 0.0
            )

            # Hours since maintenance
            hours_maint = float(
                group["hours_since_maintenance"].max()
                if "hours_since_maintenance" in group.columns
                else 0
            )

            # Average tilt severity (normalized by tilt limit)
            avg_tilt = float(
                group["tilt_angle_deg"].mean()
                if "tilt_angle_deg" in group.columns
                else 0
            )
            avg_tilt_severity = min(avg_tilt / TILT_LIMIT, 1.0)

            features[str(asset_id)] = {
                "total_engine_hours": total_engine_hours,
                "idle_ratio": idle_ratio,
                "anomaly_count_30d": 0.0,  # Updated below
                "hours_since_maintenance": hours_maint,
                "avg_tilt_severity": avg_tilt_severity,
            }

        # Overlay anomaly counts
        if anomaly_history:
            for anomaly in anomaly_history:
                aid = anomaly.get("asset_id")
                if aid and aid in features:
                    features[aid]["anomaly_count_30d"] += 1.0

        return features

    def _compute_normalization_ranges(
        self, all_features: dict[str, dict[str, float]]
    ) -> dict[str, tuple[float, float]]:
        """Compute min/max per feature across all assets for normalization."""
        ranges: dict[str, tuple[float, float]] = {}
        feature_names = list(self.weights.keys())

        for fname in feature_names:
            values = [f[fname] for f in all_features.values() if fname in f]
            if values:
                ranges[fname] = (min(values), max(values))
            else:
                ranges[fname] = (0.0, 1.0)

        return ranges

    def _normalize(self, value: float, feature_name: str) -> float:
        """Min-max normalize a feature value to [0, 1]."""
        if feature_name not in self._feature_ranges:
            return 0.0
        lo, hi = self._feature_ranges[feature_name]
        if hi <= lo:
            return 0.0
        return float(np.clip((value - lo) / (hi - lo), 0.0, 1.0))

    # ── Fit ──────────────────────────────────────────────────────────────

    def fit(
        self,
        df: pd.DataFrame,
        anomaly_history: list[dict[str, Any]] | None = None,
    ) -> "MaintenanceRiskModel":
        """Compute per-asset features and normalization ranges.

        Parameters
        ----------
        df : pd.DataFrame
            Full telemetry DataFrame (must include internal columns).
        anomaly_history : list[dict], optional
            List of anomaly dicts from ``AnomalyDetector.predict()``.

        Returns
        -------
        MaintenanceRiskModel
            self, for chaining.
        """
        self._asset_features = self._compute_asset_features(df, anomaly_history)
        self._feature_ranges = self._compute_normalization_ranges(
            self._asset_features
        )
        self._fitted = True
        return self

    # ── Predict ──────────────────────────────────────────────────────────

    def predict(
        self,
        asset_id: str,
        current_telemetry: dict[str, float] | None = None,
        recent_anomaly_count: int | None = None,
    ) -> dict[str, Any]:
        """Compute risk score for a single asset using live state.

        When called with ``current_telemetry`` and ``recent_anomaly_count``,
        the risk score reflects the asset's **current** condition — not a
        stale snapshot from training time. The normalization ranges from
        ``fit()`` are still used; only the feature values are overridden.

        Parameters
        ----------
        asset_id : str
            Asset identifier.
        current_telemetry : dict, optional
            Live telemetry state for the asset. Expected keys:
            ``engine_hours``, ``idle_hours``, ``hours_since_maintenance``,
            ``tilt_angle_deg``. If ``None``, falls back to training-time
            snapshot (useful for batch scoring during development).
        recent_anomaly_count : int, optional
            Number of anomalies for this asset in the last 30 days.
            If ``None``, falls back to the count computed during ``fit()``.

        Returns
        -------
        dict
            Risk assessment dict matching the output contract.

        Raises
        ------
        KeyError
            If the asset was not seen during fit and no current_telemetry
            is provided.
        """
        # Build feature dict: start from training snapshot, overlay live data
        if asset_id in self._asset_features:
            features = dict(self._asset_features[asset_id])
        elif current_telemetry is not None:
            # Asset not in training set — bootstrap from live data
            features = {
                "total_engine_hours": 0.0,
                "idle_ratio": 0.0,
                "anomaly_count_30d": 0.0,
                "hours_since_maintenance": 0.0,
                "avg_tilt_severity": 0.0,
            }
        else:
            raise KeyError(
                f"Asset {asset_id!r} not found in training data and no "
                f"current_telemetry provided. "
                f"Available: {list(self._asset_features.keys())[:5]}..."
            )

        # Override with live telemetry if provided
        if current_telemetry is not None:
            if "engine_hours" in current_telemetry:
                features["total_engine_hours"] = current_telemetry["engine_hours"]
            if "idle_hours" in current_telemetry and "engine_hours" in current_telemetry:
                eh = current_telemetry["engine_hours"]
                features["idle_ratio"] = (
                    current_telemetry["idle_hours"] / eh if eh > 0 else 0.0
                )
            if "hours_since_maintenance" in current_telemetry:
                features["hours_since_maintenance"] = current_telemetry[
                    "hours_since_maintenance"
                ]
            if "tilt_angle_deg" in current_telemetry:
                features["avg_tilt_severity"] = min(
                    current_telemetry["tilt_angle_deg"] / TILT_LIMIT, 1.0
                )

        # Override anomaly count if provided
        if recent_anomaly_count is not None:
            features["anomaly_count_30d"] = float(recent_anomaly_count)

        # Compute weighted score
        raw_score = 0.0
        normalized_values: dict[str, float] = {}
        for fname, weight in self.weights.items():
            norm_val = self._normalize(features.get(fname, 0.0), fname)
            normalized_values[fname] = norm_val
            raw_score += weight * norm_val

        risk_score = float(np.clip(raw_score, 0.0, 1.0))

        # Risk tier
        if risk_score >= 0.7:
            risk_tier = "HIGH"
        elif risk_score >= 0.4:
            risk_tier = "MEDIUM"
        else:
            risk_tier = "LOW"

        # Predicted failure window (rough heuristic)
        predicted_failure_window_days = max(1, round(30 * (1 - risk_score)))

        # Contributing factors: features whose normalized value > 0.6
        contributing_factors = [
            FACTOR_LABELS[fname]
            for fname, norm_val in normalized_values.items()
            if norm_val > 0.6 and fname in FACTOR_LABELS
        ]

        return {
            "asset_id": asset_id,
            "risk_score": round(risk_score, 2),
            "risk_tier": risk_tier,
            "predicted_failure_window_days": predicted_failure_window_days,
            "contributing_factors": contributing_factors,
        }

    def predict_all(self) -> list[dict[str, Any]]:
        """Compute risk scores for all fitted assets.

        Returns
        -------
        list[dict]
            List of risk dicts, one per asset.
        """
        return [
            self.predict(aid) for aid in self._asset_features
        ]

    # ── Persistence ──────────────────────────────────────────────────────

    def save(self, path: str = "models/maintenance_risk.joblib") -> None:
        """Save the model state to disk.

        Parameters
        ----------
        path : str
            Output file path.
        """
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        state = {
            "weights": self.weights,
            "asset_features": self._asset_features,
            "feature_ranges": self._feature_ranges,
            "fitted": self._fitted,
        }
        joblib.dump(state, path)

    @classmethod
    def load(
        cls, path: str = "models/maintenance_risk.joblib"
    ) -> "MaintenanceRiskModel":
        """Load a saved model from disk.

        Parameters
        ----------
        path : str
            Saved model file path.

        Returns
        -------
        MaintenanceRiskModel
            Loaded instance.
        """
        state = joblib.load(path)
        model = cls(weights=state["weights"])
        model._asset_features = state["asset_features"]
        model._feature_ranges = state["feature_ranges"]
        model._fitted = state["fitted"]
        return model
