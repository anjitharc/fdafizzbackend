from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class FoodItemCreate(BaseModel):
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    price: float
    discount_percent: float = 0.0
    preparation_time: Optional[int] = None
    is_available: bool = True


class FoodItemUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    discount_percent: Optional[float] = None
    preparation_time: Optional[int] = None
    is_available: Optional[bool] = None


class FoodItemResponse(BaseModel):
    id: int
    restaurant_id: int
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    price: float
    discount_percent: float = 0.0
    preparation_time: Optional[int] = None
    image_url: Optional[str] = None
    is_available: bool
    created_at: datetime

    class Config:
        from_attributes = True
