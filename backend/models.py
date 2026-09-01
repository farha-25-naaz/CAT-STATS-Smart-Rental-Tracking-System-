#pydantic schemas: asseststatus liveasset, checkoutRequest, checkinRequest, ActionResponse and DayUsage
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class AssetStatus(str, Enum):
    ACTIVE = "ACTIVE"
    IDLE = "IDLE"
    OVERDUE = "OVERDUE"
    UNASSIGNED = "UNASSIGNED"
    SAFETY_LOCKOUT = "SAFETY_LOCKOUT"


class LiveAsset(BaseModel):
    asset_id: str
    type: Optional[str] = None
    status: Optional[str] = None
    current_site_id: Optional[str] = None
    site_name: Optional[str] = None
    current_operator_id: Optional[str] = None
    check_out_date: Optional[datetime] = None
    check_in_date: Optional[datetime] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    # latest telemetry snapshot
    recorded_at: Optional[datetime] = None
    speed_kmh: Optional[float] = None
    tilt_angle_deg: Optional[float] = None
    engine_hours: Optional[float] = None
    idle_hours: Optional[float] = None
    fuel_level_pct: Optional[float] = None
    is_anomaly: Optional[bool] = None
    # latest unresolved alert (if any)
    latest_anomaly_type: Optional[str] = None
    latest_anomaly_reason: Optional[str] = None
    latest_anomaly_severity: Optional[str] = None
    # maintenance risk (if scored)
    risk_tier: Optional[str] = None
    risk_score: Optional[float] = None
    # commercial
    rental_rate_per_day: Optional[float] = None
    idle_cost_per_hour: Optional[float] = None


class Site(BaseModel):
    site_id: str
    site_name: Optional[str] = None
    center_lat: Optional[float] = None
    center_lng: Optional[float] = None
    geofence_radius_meters: Optional[float] = None


class ForecastPoint(BaseModel):
    date: str
    units_needed: int


class AssetForecast(BaseModel):
    site_id: str
    equipment_type: str
    forecast_horizon_days: int
    confidence: float
    predicted_demand: List[ForecastPoint]


class ForecastResponse(BaseModel):
    forecast_generated_at: str
    horizon_days: int
    forecasts: List[AssetForecast]


class CheckOutRequest(BaseModel):
    asset_id: str
    site_id: str
    operator_id: str
    check_in_date: datetime


class CheckInRequest(BaseModel):
    asset_id: str


class ActionResponse(BaseModel):
    asset_id: str
    status: str
    message: str


class DayUsage(BaseModel):
    date: str
    engine_hours_delta: float
    idle_hours_delta: float
    avg_fuel_level_pct: Optional[float] = None


# --- Phase 2: ML pipeline ingest contracts ---


class AnomalyType(str, Enum):
    UNAUTHORIZED_MOVEMENT = "UNAUTHORIZED_MOVEMENT"
    EXCESSIVE_IDLE = "EXCESSIVE_IDLE"
    GEOFENCE_BREACH = "GEOFENCE_BREACH"
    SAFETY_HAZARD = "SAFETY_HAZARD"
    IRREGULAR_USAGE = "IRREGULAR_USAGE"


class TelemetryIngest(BaseModel):
    asset_id: str
    site_id: Optional[str] = None
    lat: float
    lng: float
    heading_angle: Optional[float] = None
    speed_kmh: Optional[float] = None
    engine_rpm: Optional[float] = None
    tilt_angle: Optional[float] = None
    status: Optional[str] = None
    is_geofence_breach: bool = False
    timestamp: datetime
    # optional cumulative fields — carried forward from last row if absent
    engine_hours: Optional[float] = None
    idle_hours: Optional[float] = None
    fuel_level_pct: Optional[float] = None


class AnomalyIngest(BaseModel):
    asset_id: str
    is_anomaly: bool
    anomaly_type: AnomalyType
    anomaly_score: Optional[float] = None
    detected_at: datetime
    reason: Optional[str] = None


class RiskIngest(BaseModel):
    asset_id: str
    risk_score: float
    risk_tier: str
    predicted_failure_window_days: Optional[int] = None
    contributing_factors: List[str] = []


class SummarySeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class SummaryIngest(BaseModel):
    asset_id: str
    summary: str
    severity: Optional[SummarySeverity] = None
    generated_at: Optional[datetime] = None


# --- Phase 4: safety lockout override / clearance ---


class SafetyOverrideRequest(BaseModel):
    asset_id: str
    pin: str
    supervisor_id: str
    resolution_note: Optional[str] = None
    resume_status: str = "ACTIVE"


# --- Phase 6: demo safety net ---


class DemoReplayRequest(BaseModel):
    scenario: str = "safety_breach"
    asset_id: str
