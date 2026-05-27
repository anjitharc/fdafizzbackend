from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DeliverySettingsUpdate(BaseModel):
    normal_base_charge: Optional[float] = None
    normal_per_km: Optional[float] = None
    normal_min_km: Optional[float] = None
    normal_eta: Optional[str] = None
    fast_base_charge: Optional[float] = None
    fast_per_km: Optional[float] = None
    fast_min_km: Optional[float] = None
    fast_eta: Optional[str] = None


class DeliverySettingsResponse(BaseModel):
    id: int
    normal_base_charge: float
    normal_per_km: float
    normal_min_km: float
    normal_eta: str
    fast_base_charge: float
    fast_per_km: float
    fast_min_km: float
    fast_eta: str
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
