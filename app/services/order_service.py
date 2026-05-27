from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.order import Order, OrderItem, OrderStatus
from app.models.delivery_location import DeliveryLocation
from app.models.food_item import FoodItem
from app.schemas.order import OrderCreate, OrderResponse, OrderItemResponse
from fastapi import HTTPException, status


def create_order(db: Session, customer_id: int, order_data: OrderCreate) -> Order:
    """Create a new order with items."""
    # Calculate total amount
    total_amount = 0.0
    order_items = []

    for item in order_data.items:
        food_item = db.query(FoodItem).filter(FoodItem.id == item.food_item_id).first()
        if not food_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Food item {item.food_item_id} not found",
            )
        if not food_item.is_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Food item '{food_item.name}' is not available",
            )
        item_price = food_item.price * item.quantity
        total_amount += item_price
        order_items.append({
            "food_item_id": item.food_item_id,
            "quantity": item.quantity,
            "price": food_item.price,
        })

    # Create order
    order = Order(
        customer_id=customer_id,
        restaurant_id=order_data.restaurant_id,
        status=OrderStatus.PLACED,
        total_amount=total_amount,
        delivery_address=order_data.delivery_address,
        delivery_lat=order_data.delivery_lat,
        delivery_lng=order_data.delivery_lng,
    )
    db.add(order)
    db.flush()  # Get order ID

    # Create order items
    for item_data in order_items:
        order_item = OrderItem(
            order_id=order.id,
            food_item_id=item_data["food_item_id"],
            quantity=item_data["quantity"],
            price=item_data["price"],
        )
        db.add(order_item)

    db.commit()
    db.refresh(order)
    return order


def format_order_response(order: Order) -> dict:
    """Format an order with related data for response."""
    items = []
    for item in order.items:
        food_item_name = item.food_item.name if item.food_item else None
        items.append({
            "id": item.id,
            "food_item_id": item.food_item_id,
            "quantity": item.quantity,
            "price": item.price,
            "food_item_name": food_item_name,
        })

    delivery_location = order.delivery_staff.delivery_location if order.delivery_staff else None

    return {
        "id": order.id,
        "customer_id": order.customer_id,
        "restaurant_id": order.restaurant_id,
        "delivery_staff_id": order.delivery_staff_id,
        "status": order.status.value if order.status else None,
        "total_amount": order.total_amount,
        "delivery_address": order.delivery_address,
        "delivery_lat": order.delivery_lat,
        "delivery_lng": order.delivery_lng,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
        "items": items,
        "customer_name": order.customer.name if order.customer else None,
        "restaurant_name": order.restaurant.name if order.restaurant else None,
        "delivery_staff_name": order.delivery_staff.name if order.delivery_staff else None,
        "delivery_staff_latitude": delivery_location.latitude if delivery_location else None,
        "delivery_staff_longitude": delivery_location.longitude if delivery_location else None,
        "delivery_staff_location_updated_at": delivery_location.updated_at if delivery_location else None,
    }
