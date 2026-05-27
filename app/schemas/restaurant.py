from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class RestaurantCreate(BaseModel):
    name: str
    contact: str
    latitude: float
    longitude: float
    zone_id: Optional[int] = None


class RestaurantUpdate(BaseModel):
    name: Optional[str] = None
    contact: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    zone_id: Optional[int] = None
    is_active: Optional[int] = None


class RestaurantResponse(BaseModel):
    id: int
    name: str
    contact: str
    images: Optional[List[str]] = None
    latitude: float
    longitude: float
    zone_id: Optional[int] = None
    is_active: int
    created_at: datetime

    class Config:
        from_attributes = True
