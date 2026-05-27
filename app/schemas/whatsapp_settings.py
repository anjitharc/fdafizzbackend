from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class WhatsAppSettingsUpdate(BaseModel):
    session_id: Optional[str] = None
    api_key: Optional[str] = None
    otp_message_template: Optional[str] = None
    otp_header: Optional[str] = None


class WhatsAppSettingsResponse(BaseModel):
    id: int
    session_id: Optional[str] = None
    api_key: Optional[str] = None          # masked on GET
    otp_message_template: str
    otp_header: str
    updated_at: Optional[datetime] = None
    is_configured: bool = False            # computed field

    class Config:
        from_attributes = True


class WhatsAppTestRequest(BaseModel):
    phone: str
    message: Optional[str] = "This is a test message from FIZZ Delivery."
