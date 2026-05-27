"""
Notification Service (Stub)

This is a placeholder implementation for push notifications.
In production, integrate with Firebase Cloud Messaging (FCM) or similar service.
"""
from typing import Optional


def notify_new_order(order_id: int, restaurant_name: str, zone_id: Optional[int] = None):
    """Notify delivery staff about a new order."""
    print(f"[NOTIFICATION] New order #{order_id} from {restaurant_name} (Zone: {zone_id})")


def notify_order_assigned(order_id: int, staff_id: int, staff_name: str):
    """Notify delivery staff that an order has been assigned to them."""
    print(f"[NOTIFICATION] Order #{order_id} assigned to {staff_name} (ID: {staff_id})")


def notify_order_status_change(order_id: int, customer_id: int, new_status: str):
    """Notify customer about order status change."""
    print(f"[NOTIFICATION] Order #{order_id} status changed to '{new_status}' for customer {customer_id}")


def notify_order_delivered(order_id: int, customer_id: int):
    """Notify customer that order has been delivered."""
    print(f"[NOTIFICATION] Order #{order_id} delivered to customer {customer_id}")
