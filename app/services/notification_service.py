"""
Notification service for order-related messages.

Order notifications are best-effort: failures are logged and never block the
order lifecycle.
"""
from typing import Optional

from app.database import SessionLocal
from app.models.order import Order
from app.models.user import User, UserRole
from app.services.otp_service import send_via_whatsapp


WHATSAPP_HEADER = "FIZZ Delivery"


def _send_whatsapp(phone: Optional[str], message: str) -> bool:
    if not phone:
        print("[NOTIFICATION] WhatsApp skipped: recipient phone missing")
        return False
    try:
        return send_via_whatsapp(phone=phone, message=message, header=WHATSAPP_HEADER)
    except Exception as e:
        print(f"[NOTIFICATION] WhatsApp send failed for {phone}: {e}")
        return False


def notify_new_order(order_id: int, restaurant_name: str, zone_id: Optional[int] = None):
    """Notify zone manager(s) about a new order in their zone."""
    print(f"[NOTIFICATION] New order #{order_id} from {restaurant_name} (Zone: {zone_id})")
    if not zone_id:
        print(f"[NOTIFICATION] WhatsApp skipped for order #{order_id}: restaurant has no zone")
        return

    db = SessionLocal()
    try:
        managers = db.query(User).filter(
            User.role == UserRole.ZONE_MANAGER,
            User.zone_id == zone_id,
            User.is_active == True,
        ).all()
        if not managers:
            print(f"[NOTIFICATION] WhatsApp skipped for order #{order_id}: no active zone manager for zone {zone_id}")
            return

        message = (
            f"New order #{order_id} received from {restaurant_name}. "
            "Please review and assign a delivery staff."
        )
        for manager in managers:
            _send_whatsapp(manager.phone, message)
    except Exception as e:
        print(f"[NOTIFICATION] Failed to notify zone manager(s) for order #{order_id}: {e}")
    finally:
        db.close()


def notify_order_assigned(order_id: int, staff_id: int, staff_name: str):
    """Notify delivery staff that an order has been assigned to them."""
    print(f"[NOTIFICATION] Order #{order_id} assigned to {staff_name} (ID: {staff_id})")

    db = SessionLocal()
    try:
        staff = db.query(User).filter(
            User.id == staff_id,
            User.role == UserRole.DELIVERY_STAFF,
            User.is_active == True,
        ).first()
        if not staff:
            print(f"[NOTIFICATION] WhatsApp skipped for order #{order_id}: delivery staff not found")
            return

        order = db.query(Order).filter(Order.id == order_id).first()
        restaurant_name = order.restaurant.name if order and order.restaurant else "the restaurant"
        delivery_address = order.delivery_address if order else "the customer location"
        message = (
            f"Order #{order_id} has been assigned to you. "
            f"Pickup from {restaurant_name}. "
            f"Deliver to: {delivery_address}."
        )
        _send_whatsapp(staff.phone, message)
    except Exception as e:
        print(f"[NOTIFICATION] Failed to notify delivery staff for order #{order_id}: {e}")
    finally:
        db.close()


def notify_order_status_change(order_id: int, customer_id: int, new_status: str):
    """Notify customer about order status change."""
    print(f"[NOTIFICATION] Order #{order_id} status changed to '{new_status}' for customer {customer_id}")


def notify_order_delivered(order_id: int, customer_id: int):
    """Notify customer that order has been delivered."""
    print(f"[NOTIFICATION] Order #{order_id} delivered to customer {customer_id}")
