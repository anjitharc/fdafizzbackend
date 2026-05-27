from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from app.database import Base


class WhatsAppSettings(Base):
    __tablename__ = "whatsapp_settings"

    id = Column(Integer, primary_key=True, default=1)
    session_id = Column(String(255), nullable=True)
    api_key = Column(String(500), nullable=True)
    otp_message_template = Column(
        String(500),
        default="Your FIZZ Delivery OTP is: {otp}. Valid for 5 minutes. Do not share this code.",
    )
    otp_header = Column(String(100), default="FIZZ Delivery OTP")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
