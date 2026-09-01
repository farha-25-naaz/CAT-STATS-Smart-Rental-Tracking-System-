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
    current_operator_id: Optional[str] = None
    check_in_date: Optional[datetime] = None
    lat: Optional[float] = None
    lng: Optional[float] = None


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
