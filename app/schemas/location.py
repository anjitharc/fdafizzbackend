from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class LocationUpdate(BaseModel):
    latitude: float
    longitude: float


class LocationResponse(BaseModel):
    staff_id: int
    latitude: float
    longitude: float
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
