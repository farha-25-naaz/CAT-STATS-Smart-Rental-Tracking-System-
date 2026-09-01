"""
Per-site per-equipment-type ARIMA demand forecaster.

Predicts daily ``units_needed`` over a configurable horizon.
Falls back to seasonal naive when the time series is too short
(< ``min_history_days``) or ARIMA fails to converge.
"""

from __future__ import annotations

import itertools
import os
import warnings
from datetime import datetime, timedelta, timezone
from typing import Any

import joblib
import numpy as np
import pandas as pd

# Suppress ARIMA convergence warnings during grid search
warnings.filterwarnings("ignore", category=UserWarning, module="statsmodels")


class DemandForecaster:
    """ARIMA-based demand forecaster for construction equipment.

    Parameters
    ----------
    horizon_days : int
        Number of days to forecast.
    min_history_days : int
        Minimum days of history required for ARIMA. Groups with fewer days
        fall back to seasonal naive.
    """

    def __init__(
        self,
        horizon_days: int = 14,
        min_history_days: int = 30,
    ) -> None:
        self.horizon_days = horizon_days
        self.min_history_days = min_history_days

        # Stores {(site_id, equipment_type): model_state}
        self._models: dict[tuple[str, str], dict[str, Any]] = {}
        self._fitted = False

    # ── ARIMA order selection ────────────────────────────────────────────

    @staticmethod
    def _find_best_order(
        series: pd.Series,
    ) -> tuple[int, int, int]:
        """Grid-search ARIMA order by AIC.

        Searches p ∈ [0,3], d ∈ [0,2], q ∈ [0,3] and returns the
        (p, d, q) with the lowest AIC.
        """
        from statsmodels.tsa.arima.model import ARIMA

        best_aic = float("inf")
        best_order = (1, 1, 1)

        for p, d, q in itertools.product(range(4), range(3), range(4)):
            if p == 0 and q == 0:
                continue  # Skip trivial (0,d,0)
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    model = ARIMA(series, order=(p, d, q))
                    result = model.fit()
                    if result.aic < best_aic:
                        best_aic = result.aic
                        best_order = (p, d, q)
            except Exception:
                continue

        return best_order

    # ── Seasonal naive fallback ──────────────────────────────────────────

    @staticmethod
    def _seasonal_naive_forecast(
        series: pd.Series, horizon: int, period: int = 7
    ) -> list[int]:
        """Repeat the last ``period`` values cyclically."""
        tail = series.tail(period).tolist()
        forecast = []
        for i in range(horizon):
            forecast.append(max(0, int(round(tail[i % len(tail)]))))
        return forecast

    # ── Fit ───────────────────────────────────────────────────────────────

    def fit(self, df: pd.DataFrame) -> "DemandForecaster":
        """Fit one ARIMA model per ``(site_id, equipment_type)`` group.

        Parameters
        ----------
        df : pd.DataFrame
            Columns: ``date``, ``site_id``, ``equipment_type``, ``units_used``.

        Returns
        -------
        DemandForecaster
            self, for chaining.
        """
        from statsmodels.tsa.arima.model import ARIMA

        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

        groups = df.groupby(["site_id", "equipment_type"])

        for (site_id, eq_type), group in groups:
            series = group.set_index("date")["units_used"].asfreq("D")
            series = series.fillna(0)

            model_state: dict[str, Any] = {
                "site_id": site_id,
                "equipment_type": eq_type,
                "method": "seasonal_naive",
                "order": None,
                "arima_result": None,
                "series": series,
                "confidence": 0.5,  # default for naive
            }

            if len(series) >= self.min_history_days:
                try:
                    # Holdout last 7 days for MAPE
                    train = series.iloc[:-7]
                    holdout = series.iloc[-7:]

                    order = self._find_best_order(train)

                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        model = ARIMA(train, order=order)
                        result = model.fit()

                    # Compute MAPE on holdout
                    holdout_pred = result.forecast(steps=7)
                    mape = np.mean(
                        np.abs(
                            (holdout.values - holdout_pred.values)
                            / np.maximum(holdout.values, 1)
                        )
                    )
                    confidence = float(np.clip(1.0 - mape, 0.0, 1.0))

                    # Re-fit on full series
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        full_model = ARIMA(series, order=order)
                        full_result = full_model.fit()

                    model_state.update(
                        {
                            "method": "arima",
                            "order": order,
                            "arima_result": full_result,
                            "confidence": round(confidence, 2),
                        }
                    )
                except Exception:
                    pass  # Fall back to seasonal naive

            self._models[(site_id, eq_type)] = model_state

        self._fitted = True
        return self

    # ── Predict ──────────────────────────────────────────────────────────

    def predict(self, site_id: str, equipment_type: str) -> dict[str, Any]:
        """Forecast demand for a single ``(site_id, equipment_type)`` group.

        Parameters
        ----------
        site_id : str
            Site identifier.
        equipment_type : str
            Equipment category.

        Returns
        -------
        dict
            Forecast dict matching the output contract.

        Raises
        ------
        KeyError
            If the group was not seen during fit.
        """
        key = (site_id, equipment_type)
        if key not in self._models:
            raise KeyError(
                f"No model fitted for ({site_id}, {equipment_type}). "
                f"Available groups: {list(self._models.keys())}"
            )

        state = self._models[key]
        series = state["series"]
        last_date = series.index[-1]

        if state["method"] == "arima" and state["arima_result"] is not None:
            forecast_values = state["arima_result"].forecast(
                steps=self.horizon_days
            )
            predicted = [
                max(0, int(round(v))) for v in forecast_values.values
            ]
        else:
            predicted = self._seasonal_naive_forecast(
                series, self.horizon_days
            )

        # Build date list
        predicted_demand = []
        for i, units in enumerate(predicted):
            forecast_date = last_date + timedelta(days=i + 1)
            predicted_demand.append(
                {
                    "date": forecast_date.strftime("%Y-%m-%d"),
                    "units_needed": units,
                }
            )

        return {
            "site_id": site_id,
            "equipment_type": equipment_type,
            "forecast_generated_at": datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "forecast_horizon_days": self.horizon_days,
            "predicted_demand": predicted_demand,
            "confidence": state["confidence"],
        }

    def predict_all(self) -> list[dict[str, Any]]:
        """Forecast demand for all fitted groups.

        Returns
        -------
        list[dict]
            List of forecast dicts, one per ``(site_id, equipment_type)`` group.
        """
        return [
            self.predict(site_id, eq_type)
            for (site_id, eq_type) in self._models
        ]

    # ── Persistence ──────────────────────────────────────────────────────

    def save(self, path: str = "models/demand_forecaster.joblib") -> None:
        """Save the fitted models to disk.

        Parameters
        ----------
        path : str
            Output file path.
        """
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        state = {
            "models": self._models,
            "params": {
                "horizon_days": self.horizon_days,
                "min_history_days": self.min_history_days,
            },
            "fitted": self._fitted,
        }
        joblib.dump(state, path)

    @classmethod
    def load(
        cls, path: str = "models/demand_forecaster.joblib"
    ) -> "DemandForecaster":
        """Load fitted models from disk.

        Parameters
        ----------
        path : str
            Saved model file path.

        Returns
        -------
        DemandForecaster
            Loaded instance with restored models.
        """
        state = joblib.load(path)
        forecaster = cls(**state["params"])
        forecaster._models = state["models"]
        forecaster._fitted = state["fitted"]
        return forecaster
