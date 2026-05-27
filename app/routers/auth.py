from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    SendOTPRequest,
    VerifyOTPRequest,
    RefreshTokenRequest,
)
from app.services.auth_service import authenticate_user, create_tokens, refresh_access_token
from app.services.otp_service import generate_otp, verify_otp

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Login with email and password (for admin, zone_manager, delivery_staff)."""
    user = authenticate_user(db, request.email, request.password)
    return create_tokens(user)


@router.post("/customer/send-otp")
def send_otp(request: SendOTPRequest, db: Session = Depends(get_db)):
    """Send OTP to customer phone number."""
    otp = generate_otp(request.phone)
    return {"message": "OTP sent successfully", "phone": request.phone}


@router.post("/customer/verify-otp", response_model=TokenResponse)
def customer_verify_otp(request: VerifyOTPRequest, db: Session = Depends(get_db)):
    """Verify OTP and return JWT tokens. Creates customer if not exists."""
    if not verify_otp(request.phone, request.otp):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OTP",
        )

    # Find or create customer
    user = db.query(User).filter(User.phone == request.phone).first()
    if not user:
        # Create new customer
        name = request.name or f"Customer_{request.phone[-4:]}"
        user = User(
            name=name,
            phone=request.phone,
            role=UserRole.CUSTOMER,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    return create_tokens(user)


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Refresh access token using refresh token."""
    return refresh_access_token(db, request.refresh_token)
