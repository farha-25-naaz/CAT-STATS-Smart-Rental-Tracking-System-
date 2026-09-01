"""Expose the trained ``DemandForecaster`` (ARIMA per site x equipment type).

* ``GET /forecast``  — predicted daily ``units_needed`` over a horizon.

Query params (all optional):
    site_id         filter to one site
    equipment_type  filter to one equipment type (e.g. "Excavator")
    horizon         forecast length in days (default 14, clamped 1..90)
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ml_orchestration import get_demand_forecaster
from models import AssetForecast, ForecastPoint, ForecastResponse

router = APIRouter(tags=["forecast"])


@router.get("/forecast", response_model=ForecastResponse)
def get_forecast(
    site_id: Optional[str] = Query(None),
    equipment_type: Optional[str] = Query(None),
    horizon: int = Query(14, ge=1, le=90),
):
    forecaster = get_demand_forecaster()

    keys = [
        (s, e)
        for (s, e) in forecaster._models
        if (site_id is None or s == site_id)
        and (equipment_type is None or e == equipment_type)
    ]
    if not keys:
        raise HTTPException(
            status_code=404,
            detail=(
                "No fitted forecast group matches "
                f"site_id={site_id!r} equipment_type={equipment_type!r}"
            ),
        )

    original_horizon = forecaster.horizon_days
    forecaster.horizon_days = horizon
    try:
        forecasts = []
        for s, e in keys:
            p = forecaster.predict(s, e)
            forecasts.append(
                AssetForecast(
                    site_id=s,
                    equipment_type=e,
                    forecast_horizon_days=p["forecast_horizon_days"],
                    confidence=p["confidence"],
                    predicted_demand=[
                        ForecastPoint(date=d["date"], units_needed=d["units_needed"])
                        for d in p["predicted_demand"]
                    ],
                )
            )
    finally:
        forecaster.horizon_days = original_horizon

    return ForecastResponse(
        forecast_generated_at=datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        horizon_days=horizon,
        forecasts=forecasts,
    )
