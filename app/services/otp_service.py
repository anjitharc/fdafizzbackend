import random
import time
import requests
from typing import Dict, Tuple
from app.config import get_settings

settings = get_settings()

# In-memory OTP store: {phone: (otp, expiry_timestamp)}
_otp_store: Dict[str, Tuple[str, float]] = {}

WHATSAPP_API_URL = "https://whatsapp.assoftwares.com/api/external/send"


def _load_whatsapp_settings():
    """Load WhatsApp settings from DB (creates own session to work outside request context)."""
    try:
        from app.database import SessionLocal
        from app.models.whatsapp_settings import WhatsAppSettings
        db = SessionLocal()
        try:
            return db.query(WhatsAppSettings).filter(WhatsAppSettings.id == 1).first()
        finally:
            db.close()
    except Exception as e:
        print(f"[OTP] Failed to load WhatsApp settings: {e}")
        return None


def _format_whatsapp_phone(phone: str) -> str:
    """Format phone number for WhatsApp API using India country code."""
    digits = ''.join(ch for ch in phone if ch.isdigit())
    if digits.startswith('91'):
        return digits
    if len(digits) == 10:
        return f"91{digits}"
    if digits.startswith('0') and len(digits) == 11:
        return f"91{digits[1:]}"
    return digits


def send_via_whatsapp(phone: str, message: str, header: str = "FIZZ Delivery") -> bool:
    """
    Send a message via the WhatsApp API.
    Returns True on success, False on failure.
    """
    wa = _load_whatsapp_settings()
    if not wa or not wa.session_id or not wa.api_key:
        print(f"[OTP] WhatsApp not configured — message not sent to {phone}")
        return False

    formatted_phone = _format_whatsapp_phone(phone)
    payload = {
        "session_id": wa.session_id,
        "phone": formatted_phone,
        "message": message,
        "header": header,
    }
    headers = {
        "x-api-key": wa.api_key,
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(WHATSAPP_API_URL, json=payload, headers=headers, timeout=10)
        if resp.status_code == 200:
            print(f"[OTP] WhatsApp message sent to {phone}")
            return True
        else:
            print(f"[OTP] WhatsApp API error {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        print(f"[OTP] WhatsApp send exception: {e}")
        return False


def generate_otp(phone: str) -> str:
    """Generate a 6-digit OTP, store it, and send via WhatsApp."""
    otp = str(random.randint(100000, 999999))
    expiry = time.time() + settings.OTP_EXPIRY_SECONDS
    _otp_store[phone] = (otp, expiry)

    # Always log to console for debugging
    print(f"[OTP] Phone: {phone}, OTP: {otp}")

    # Load template from WhatsApp settings if available
    wa = _load_whatsapp_settings()
    if wa and wa.session_id and wa.api_key:
        template = wa.otp_message_template or "Your FIZZ Delivery OTP is: {otp}. Valid for 5 minutes."
        header = wa.otp_header or "FIZZ Delivery OTP"
        message = template.replace("{otp}", otp)
        send_via_whatsapp(phone, message, header)
    else:
        print(f"[OTP] WhatsApp not configured. OTP for {phone}: {otp}")

    return otp


def verify_otp(phone: str, otp: str) -> bool:
    """Verify the OTP for a given phone number."""
    stored = _otp_store.get(phone)
    if stored is None:
        return False

    stored_otp, expiry = stored
    if time.time() > expiry:
        del _otp_store[phone]
        return False

    if stored_otp != otp:
        return False

    # OTP verified — remove from store
    del _otp_store[phone]
    return True
