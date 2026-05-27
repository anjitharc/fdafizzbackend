from datetime import datetime
from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.database import Base


class Zone(Base):
    __tablename__ = "zones"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    coordinates = Column(JSON, nullable=False)  # Array of {lat, lng} polygon points
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    zone_managers = relationship("User", back_populates="zone", foreign_keys="User.zone_id")
    restaurants = relationship("Restaurant", back_populates="zone")
