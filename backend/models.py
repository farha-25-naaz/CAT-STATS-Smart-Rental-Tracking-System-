#pydantic schemas: asseststatus liveasset, checkoutRequest, checkinRequest, ActionResponse and DayUsage
from datetime import datetime
from enum import Enum
from typing import Optional

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
