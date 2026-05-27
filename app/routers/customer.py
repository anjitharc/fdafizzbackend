from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.dependencies import require_role
from app.models.user import User, UserRole
from app.models.restaurant import Restaurant
from app.models.food_item import FoodItem
from app.models.order import Order
from app.models.delivery_location import DeliveryLocation
from app.schemas.restaurant import RestaurantResponse
from app.schemas.food_item import FoodItemResponse
from app.schemas.order import OrderCreate
from app.schemas.user import CustomerProfileUpdate, UserResponse
from app.services.zone_service import get_restaurants_for_customer_location
from app.services.order_service import create_order, format_order_response
from app.services.notification_service import notify_new_order

router = APIRouter()


@router.get("/restaurants", response_model=List[RestaurantResponse])
def list_customer_restaurants(
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    current_user: User = Depends(require_role(["customer"])),
    db: Session = Depends(get_db),
):
    """List restaurants where customer location matches an enabled zone."""
    try:
        final_lat = lat if lat is not None else float(current_user.latitude) if current_user.latitude else None
        final_lng = lng if lng is not None else float(current_user.longitude) if current_user.longitude else None
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Saved customer location is invalid")
    if final_lat is None or final_lng is None:
        raise HTTPException(status_code=400, detail="Customer location is required")
    restaurants = get_restaurants_for_customer_location(db, final_lat, final_lng)
    return restaurants


@router.get("/restaurants/{restaurant_id}/menu", response_model=List[FoodItemResponse])
def get_restaurant_menu(
    restaurant_id: int,
    current_user: User = Depends(require_role(["customer"])),
    db: Session = Depends(get_db),
):
    """Get available food items for a restaurant."""
    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    return db.query(FoodItem).filter(
        FoodItem.restaurant_id == restaurant_id,
        FoodItem.is_available == True,
    ).all()


@router.post("/orders")
def place_order(
    data: OrderCreate,
    current_user: User = Depends(require_role(["customer"])),
    db: Session = Depends(get_db),
):
    """Place a new order."""
    # Verify restaurant exists
    restaurant = db.query(Restaurant).filter(Restaurant.id == data.restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    order = create_order(db, current_user.id, data)

    # Keep the customer saved location in sync with their latest delivery location.
    current_user.address = data.delivery_address
    if data.delivery_lat is not None:
        current_user.latitude = str(data.delivery_lat)
    if data.delivery_lng is not None:
        current_user.longitude = str(data.delivery_lng)
    db.commit()
    db.refresh(current_user)

    # Notify delivery staff about new order
    notify_new_order(order.id, restaurant.name, restaurant.zone_id)

    return format_order_response(order)


@router.get("/orders")
def get_order_history(
    current_user: User = Depends(require_role(["customer"])),
    db: Session = Depends(get_db),
):
    """Get customer order history."""
    orders = db.query(Order).filter(
        Order.customer_id == current_user.id
    ).order_by(Order.created_at.desc()).all()
    return [format_order_response(order) for order in orders]


@router.get("/orders/{order_id}/delivery-location")
def get_order_delivery_location(
    order_id: int,
    current_user: User = Depends(require_role(["customer"])),
    db: Session = Depends(get_db),
):
    """Get assigned delivery staff location for a customer's order."""
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.customer_id == current_user.id,
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if not order.delivery_staff_id:
        raise HTTPException(status_code=404, detail="Delivery staff not assigned yet")

    location = db.query(DeliveryLocation).filter(
        DeliveryLocation.staff_id == order.delivery_staff_id,
    ).first()
    if not location:
        raise HTTPException(status_code=404, detail="Delivery staff location not available yet")

    return {
        "order_id": order.id,
        "staff_id": order.delivery_staff_id,
        "latitude": location.latitude,
        "longitude": location.longitude,
        "updated_at": location.updated_at,
    }


@router.get("/orders/{order_id}")
def get_order_detail(
    order_id: int,
    current_user: User = Depends(require_role(["customer"])),
    db: Session = Depends(get_db),
):
    """Get order detail with current status."""
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.customer_id == current_user.id,
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return format_order_response(order)


@router.get("/profile", response_model=UserResponse)
def get_profile(
    current_user: User = Depends(require_role(["customer"])),
    db: Session = Depends(get_db),
):
    """Get current customer profile, including saved address and location."""
    return current_user


@router.put("/profile", response_model=UserResponse)
def update_profile(
    data: CustomerProfileUpdate,
    current_user: User = Depends(require_role(["customer"])),
    db: Session = Depends(get_db),
):
    """Update customer profile (address, location)."""
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)
    return current_user
