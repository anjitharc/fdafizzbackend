import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class UserRole(str, enum.Enum):
    MASTER_ADMIN = "master_admin"
    ZONE_MANAGER = "zone_manager"
    DELIVERY_STAFF = "delivery_staff"
    CUSTOMER = "customer"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    phone = Column(String(20), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True)  # Null for OTP-only customers
    role = Column(Enum(UserRole), nullable=False)
    is_active = Column(Boolean, default=True)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=True)  # For zone managers
    address = Column(String(500), nullable=True)
    latitude = Column(String(50), nullable=True)
    longitude = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    zone = relationship("Zone", back_populates="zone_managers", foreign_keys=[zone_id])
    orders = relationship("Order", back_populates="customer", foreign_keys="Order.customer_id")
    delivery_orders = relationship("Order", back_populates="delivery_staff", foreign_keys="Order.delivery_staff_id")
    delivery_location = relationship("DeliveryLocation", back_populates="staff", uselist=False)
