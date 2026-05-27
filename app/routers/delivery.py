from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.database import get_db
from app.dependencies import require_role
from app.models.user import User, UserRole
from app.models.order import Order, OrderStatus
from app.models.delivery_location import DeliveryLocation
from app.schemas.order import OrderStatusUpdate
from app.schemas.location import LocationUpdate, LocationResponse
from app.services.order_service import format_order_response
from app.services.notification_service import notify_order_status_change
from app.routers.websocket import manager as ws_manager

router = APIRouter()


@router.get("/orders/unassigned")
def get_unassigned_orders(
    current_user: User = Depends(require_role(["delivery_staff"])),
    db: Session = Depends(get_db),
):
    """Get unassigned orders (orders without a delivery staff assigned)."""
    orders = db.query(Order).filter(
        Order.delivery_staff_id.is_(None),
        Order.status == OrderStatus.PLACED,
    ).order_by(Order.created_at.desc()).all()
    return [format_order_response(order) for order in orders]


@router.get("/orders/assigned")
def get_assigned_orders(
    current_user: User = Depends(require_role(["delivery_staff"])),
    db: Session = Depends(get_db),
):
    """Get orders assigned to this delivery staff."""
    orders = db.query(Order).filter(
        Order.delivery_staff_id == current_user.id,
        Order.status != OrderStatus.DELIVERED,
        Order.status != OrderStatus.CANCELLED,
    ).order_by(Order.created_at.desc()).all()
    return [format_order_response(order) for order in orders]


@router.get("/orders/{order_id}")
def get_order_detail(
    order_id: int,
    current_user: User = Depends(require_role(["delivery_staff"])),
    db: Session = Depends(get_db),
):
    """Get full order details."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return format_order_response(order)


@router.put("/orders/{order_id}/status")
def update_order_status(
    order_id: int,
    data: OrderStatusUpdate,
    current_user: User = Depends(require_role(["delivery_staff"])),
    db: Session = Depends(get_db),
):
    """Update order status (preparing, out_for_delivery, delivered)."""
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.delivery_staff_id == current_user.id,
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found or not assigned to you")

    # Validate status transition
    valid_statuses = ["preparing", "out_for_delivery", "delivered"]
    if data.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {valid_statuses}",
        )

    order.status = OrderStatus(data.status)
    order.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(order)

    # Notify customer
    notify_order_status_change(order.id, order.customer_id, data.status)

    # Broadcast via WebSocket
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(
                ws_manager.broadcast_order_update(order_id, {"status": data.status})
            )
    except RuntimeError:
        pass

    return format_order_response(order)


@router.post("/location", response_model=LocationResponse)
def update_location(
    data: LocationUpdate,
    current_user: User = Depends(require_role(["delivery_staff"])),
    db: Session = Depends(get_db),
):
    """Update delivery staff location (called every 30 seconds)."""
    location = db.query(DeliveryLocation).filter(
        DeliveryLocation.staff_id == current_user.id
    ).first()

    if location:
        location.latitude = data.latitude
        location.longitude = data.longitude
        location.updated_at = datetime.utcnow()
    else:
        location = DeliveryLocation(
            staff_id=current_user.id,
            latitude=data.latitude,
            longitude=data.longitude,
        )
        db.add(location)

    db.commit()
    db.refresh(location)

    # Broadcast location via WebSocket
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(
                ws_manager.broadcast_location_update(
                    current_user.id,
                    {"latitude": data.latitude, "longitude": data.longitude},
                )
            )
    except RuntimeError:
        pass

    return location


@router.get("/location/{staff_id}", response_model=LocationResponse)
def get_staff_location(
    staff_id: int,
    current_user: User = Depends(require_role(["delivery_staff", "master_admin", "zone_manager"])),
    db: Session = Depends(get_db),
):
    """Get current location of a delivery staff member."""
    location = db.query(DeliveryLocation).filter(
        DeliveryLocation.staff_id == staff_id
    ).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found for this staff")
    return location
