from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime


class ZoneCreate(BaseModel):
    name: str
    coordinates: List[Dict[str, float]]  # [{lat: float, lng: float}, ...]
    is_enabled: bool = True


class ZoneUpdate(BaseModel):
    name: Optional[str] = None
    coordinates: Optional[List[Dict[str, float]]] = None
    is_enabled: Optional[bool] = None


class ZoneResponse(BaseModel):
    id: int
    name: str
    coordinates: List[Dict[str, float]]
    is_enabled: bool = True
    created_by: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True
