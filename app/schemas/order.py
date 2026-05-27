from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class OrderItemCreate(BaseModel):
    food_item_id: int
    quantity: int = 1


class OrderCreate(BaseModel):
    restaurant_id: int
    items: List[OrderItemCreate]
    delivery_address: str
    delivery_lat: Optional[float] = None
    delivery_lng: Optional[float] = None


class OrderStatusUpdate(BaseModel):
    status: str  # preparing, out_for_delivery, delivered


class OrderAssign(BaseModel):
    delivery_staff_id: int


class OrderItemResponse(BaseModel):
    id: int
    food_item_id: int
    quantity: int
    price: float
    food_item_name: Optional[str] = None

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    id: int
    customer_id: int
    restaurant_id: int
    delivery_staff_id: Optional[int] = None
    status: str
    total_amount: float
    delivery_address: str
    delivery_lat: Optional[float] = None
    delivery_lng: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    items: List[OrderItemResponse] = []
    customer_name: Optional[str] = None
    restaurant_name: Optional[str] = None
    delivery_staff_name: Optional[str] = None

    class Config:
        from_attributes = True
