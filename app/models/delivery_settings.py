from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime
from app.database import Base


class DeliverySettings(Base):
    __tablename__ = "delivery_settings"

    id = Column(Integer, primary_key=True, default=1)

    # Normal delivery
    normal_base_charge = Column(Float, default=2.0)     # Flat base charge (currency)
    normal_per_km = Column(Float, default=1.0)          # Charge per km
    normal_min_km = Column(Float, default=1.0)          # Minimum km threshold
    normal_eta = Column(String(50), default="30-45 min")  # Estimated delivery time label

    # Fast delivery
    fast_base_charge = Column(Float, default=5.0)
    fast_per_km = Column(Float, default=2.5)
    fast_min_km = Column(Float, default=1.0)
    fast_eta = Column(String(50), default="15-20 min")

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
