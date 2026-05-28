from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional, Union
from app.database import get_db
from app.dependencies import require_role
from app.models.user import User, UserRole
from app.models.restaurant import Restaurant
from app.models.food_item import FoodItem
from app.models.zone import Zone
from app.models.order import Order, OrderStatus
from app.schemas.restaurant import RestaurantCreate, RestaurantUpdate, RestaurantResponse
from app.schemas.food_item import FoodItemCreate, FoodItemUpdate, FoodItemResponse
from app.schemas.zone import ZoneCreate, ZoneUpdate, ZoneResponse
from app.schemas.user import UserCreate, UserResponse
from app.schemas.order import OrderAssign, OrderResponse
from app.services.minio_service import upload_image, delete_image
from app.services.order_service import format_order_response
from app.services.notification_service import notify_order_assigned
from app.utils.security import hash_password
from app.models.delivery_settings import DeliverySettings
from app.schemas.delivery_settings import DeliverySettingsUpdate, DeliverySettingsResponse
from app.models.whatsapp_settings import WhatsAppSettings
from app.schemas.whatsapp_settings import WhatsAppSettingsUpdate, WhatsAppSettingsResponse, WhatsAppTestRequest

router = APIRouter()


# ==================== RESTAURANTS ====================

@router.post("/restaurants", response_model=RestaurantResponse)
def create_restaurant(
    name: str = Form(...),
    contact: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    zone_id: Optional[int] = Form(None),
    images: Union[List[UploadFile], UploadFile, None] = File(default=None),
    current_user: User = Depends(require_role(["master_admin"])),
    db: Session = Depends(get_db),
):
    """Create a new restaurant with images."""
    # Normalize: None → [], single file → [file], list → list
    if images is None:
        image_list: List[UploadFile] = []
    elif isinstance(images, list):
        image_list = images
    else:
        image_list = [images]

    image_urls = []
    for image in image_list:
        try:
            url = upload_image(image)
            image_urls.append(url)
        except Exception as e:
            print(f"Image upload failed: {e}")

    restaurant = Restaurant(
        name=name,
        contact=contact,
        latitude=latitude,
        longitude=longitude,
        zone_id=zone_id,
        images=image_urls if image_urls else None,
        created_by=current_user.id,
    )
    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)
    return restaurant


@router.get("/restaurants", response_model=List[RestaurantResponse])
def list_restaurants(
    current_user: User = Depends(require_role(["master_admin"])),
    db: Session = Depends(get_db),
):
    """List all restaurants."""
    return db.query(Restaurant).all()


@router.put("/restaurants/{restaurant_id}", response_model=RestaurantResponse)
def update_restaurant(
    restaurant_id: int,
    data: RestaurantUpdate,
    current_user: User = Depends(require_role(["master_admin"])),
    db: Session = Depends(get_db),
):
    """Update a restaurant."""
    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(restaurant, field, value)

    db.commit()
    db.refresh(restaurant)
    return restaurant


@router.delete("/restaurants/{restaurant_id}")
def delete_restaurant(
    restaurant_id: int,
    current_user: User = Depends(require_role(["master_admin"])),
    db: Session = Depends(get_db),
):
    """Delete a restaurant."""
    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    # Delete images from MinIO
    if restaurant.images:
        for img_url in restaurant.images:
            delete_image(img_url)

    db.delete(restaurant)
    db.commit()
    return {"message": "Restaurant deleted successfully"}


@router.post("/restaurants/{restaurant_id}/images", response_model=RestaurantResponse)
def add_restaurant_images(
    restaurant_id: int,
    images: Union[List[UploadFile], UploadFile, None] = File(default=None),
    current_user: User = Depends(require_role(["master_admin"])),
    db: Session = Depends(get_db),
):
    """Add more images to an existing restaurant."""
    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    if images is None:
        image_list: List[UploadFile] = []
    elif isinstance(images, list):
        image_list = images
    else:
        image_list = [images]

    existing = list(restaurant.images or [])
    for image in image_list:
        try:
            url = upload_image(image)
            existing.append(url)
        except Exception as e:
            print(f"Image upload failed: {e}")

    restaurant.images = existing
    db.commit()
    db.refresh(restaurant)
    return restaurant


@router.delete("/restaurants/{restaurant_id}/images/{image_index}", response_model=RestaurantResponse)
def remove_restaurant_image(
    restaurant_id: int,
    image_index: int,
    current_user: User = Depends(require_role(["master_admin"])),
    db: Session = Depends(get_db),
):
    """Remove an image from a restaurant by its index."""
    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    images = list(restaurant.images or [])
    if image_index < 0 or image_index >= len(images):
        raise HTTPException(status_code=400, detail="Invalid image index")

    removed_url = images.pop(image_index)
    try:
        delete_image(removed_url)
    except Exception:
        pass

    restaurant.images = images if images else None
    db.commit()
    db.refresh(restaurant)
    return restaurant


# ==================== FOOD ITEMS ====================

@router.post("/restaurants/{restaurant_id}/food-items", response_model=FoodItemResponse)
def create_food_item(
    restaurant_id: int,
    name: str = Form(...),
    category: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    price: float = Form(...),
    discount_percent: float = Form(0.0),
    preparation_time: Optional[int] = Form(None),
    is_available: bool = Form(True),
    image: Optional[UploadFile] = File(None),
    current_user: User = Depends(require_role(["master_admin"])),
    db: Session = Depends(get_db),
):
    """Create a food item under a restaurant."""
    restaurant = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    image_url = None
    if image:
        image_url = upload_image(image)

    food_item = FoodItem(
        restaurant_id=restaurant_id,
        name=name,
        category=category,
        description=description,
        price=price,
        discount_percent=discount_percent,
        preparation_time=preparation_time,
        image_url=image_url,
        is_available=is_available,
    )
    db.add(food_item)
    db.commit()
    db.refresh(food_item)
    return food_item


@router.get("/restaurants/{restaurant_id}/food-items", response_model=List[FoodItemResponse])
def list_food_items(
    restaurant_id: int,
    current_user: User = Depends(require_role(["master_admin"])),
    db: Session = Depends(get_db),
):
    """List food items for a restaurant."""
    return db.query(FoodItem).filter(FoodItem.restaurant_id == restaurant_id).all()


@router.put("/food-items/{food_item_id}", response_model=FoodItemResponse)
def update_food_item(
    food_item_id: int,
    name: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    price: Optional[float] = Form(None),
    discount_percent: Optional[float] = Form(None),
    preparation_time: Optional[int] = Form(None),
    is_available: Optional[bool] = Form(None),
    image: Optional[UploadFile] = File(None),
    current_user: User = Depends(require_role(["master_admin"])),
    db: Session = Depends(get_db),
):
    """Update a food item."""
    food_item = db.query(FoodItem).filter(FoodItem.id == food_item_id).first()
    if not food_item:
        raise HTTPException(status_code=404, detail="Food item not found")

    if name is not None:
        food_item.name = name
    if category is not None:
        food_item.category = category
    if description is not None:
        food_item.description = description
    if price is not None:
        food_item.price = price
    if discount_percent is not None:
        food_item.discount_percent = discount_percent
    if preparation_time is not None:
        food_item.preparation_time = preparation_time
    if is_available is not None:
        food_item.is_available = is_available
    if image:
        try:
            if food_item.image_url:
                delete_image(food_item.image_url)
            food_item.image_url = upload_image(image)
        except Exception as e:
            print(f"Image upload failed: {e}")

    db.commit()
    db.refresh(food_item)
    return food_item


@router.delete("/food-items/{food_item_id}")
def delete_food_item(
    food_item_id: int,
    current_user: User = Depends(require_role(["master_admin"])),
    db: Session = Depends(get_db),
):
    """Delete a food item."""
    food_item = db.query(FoodItem).filter(FoodItem.id == food_item_id).first()
    if not food_item:
        raise HTTPException(status_code=404, detail="Food item not found")

    if food_item.image_url:
        delete_image(food_item.image_url)

    db.delete(food_item)
    db.commit()
    return {"message": "Food item deleted successfully"}


# ==================== DELIVERY STAFF ====================

@router.post("/delivery-staff", response_model=UserResponse)
def create_delivery_staff(
    data: UserCreate,
    current_user: User = Depends(require_role(["master_admin"])),
    db: Session = Depends(get_db),
):
    """Create a delivery staff member."""
    # Check if email/phone already exists
    existing = db.query(User).filter(
        (User.email == data.email) | (User.phone == data.phone)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email or phone already registered")

    if data.zone_id:
        zone = db.query(Zone).filter(Zone.id == data.zone_id, Zone.is_enabled == True).first()
        if not zone:
            raise HTTPException(status_code=404, detail="Active zone not found")

    user = User(
        name=data.name,
        email=data.email,
        phone=data.phone,
        password_hash=hash_password(data.password) if data.password else None,
        role=UserRole.DELIVERY_STAFF,
        zone_id=data.zone_id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/delivery-staff", response_model=List[UserResponse])
def list_delivery_staff(
    current_user: User = Depends(require_role(["master_admin"])),
    db: Session = Depends(get_db),
):
    """List active delivery staff."""
    return db.query(User).filter(
        User.role == UserRole.DELIVERY_STAFF,
        User.is_active == True,
    ).all()


# ==================== ZONES ====================

@router.post("/zones", response_model=ZoneResponse)
def create_zone(
    data: ZoneCreate,
    current_user: User = Depends(require_role(["master_admin"])),
    db: Session = Depends(get_db),
):
    """Create a zone with polygon coordinates."""
    zone = Zone(
        name=data.name,
        coordinates=data.coordinates,
        is_enabled=data.is_enabled,
        created_by=current_user.id,
    )
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return zone


@router.get("/zones", response_model=List[ZoneResponse])
def list_zones(
    current_user: User = Depends(require_role(["master_admin"])),
    db: Session = Depends(get_db),
):
    """List all zones."""
    return db.query(Zone).all()


@router.put("/zones/{zone_id}", response_model=ZoneResponse)
def update_zone(
    zone_id: int,
    data: ZoneUpdate,
    current_user: User = Depends(require_role(["master_admin"])),
    db: Session = Depends(get_db),
):
    """Update a zone."""
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(zone, field, value)

    db.commit()
    db.refresh(zone)
    return zone


@router.delete("/zones/{zone_id}")
def delete_zone(
    zone_id: int,
    current_user: User = Depends(require_role(["master_admin"])),
    db: Session = Depends(get_db),
):
    """Delete a zone."""
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    db.delete(zone)
    db.commit()
    return {"message": "Zone deleted successfully"}


# ==================== ZONE MANAGERS ====================

@router.post("/zone-managers", response_model=UserResponse)
def create_zone_manager(
    data: UserCreate,
    current_user: User = Depends(require_role(["master_admin"])),
    db: Session = Depends(get_db),
):
    """Create a zone manager and assign to a zone."""
    existing = db.query(User).filter(
        (User.email == data.email) | (User.phone == data.phone)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email or phone already registered")

    if data.zone_id:
        zone = db.query(Zone).filter(Zone.id == data.zone_id, Zone.is_enabled == True).first()
        if not zone:
            raise HTTPException(status_code=404, detail="Active zone not found")

    user = User(
        name=data.name,
        email=data.email,
        phone=data.phone,
        password_hash=hash_password(data.password) if data.password else None,
        role=UserRole.ZONE_MANAGER,
        zone_id=data.zone_id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/zone-managers", response_model=List[UserResponse])
def list_zone_managers(
    current_user: User = Depends(require_role(["master_admin"])),
    db: Session = Depends(get_db),
):
    """List all zone managers."""
    return db.query(User).filter(User.role == UserRole.ZONE_MANAGER).all()


# ==================== ORDERS ====================

@router.get("/orders")
def list_orders(
    current_user: User = Depends(require_role(["master_admin"])),
    db: Session = Depends(get_db),
):
    """List all orders."""
    orders = db.query(Order).order_by(Order.created_at.desc()).all()
    return [format_order_response(order) for order in orders]


@router.post("/orders/{order_id}/assign")
def assign_order(
    order_id: int,
    data: OrderAssign,
    current_user: User = Depends(require_role(["master_admin"])),
    db: Session = Depends(get_db),
):
    """Assign an order to a delivery staff member."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    staff = db.query(User).filter(
        User.id == data.delivery_staff_id,
        User.role == UserRole.DELIVERY_STAFF,
        User.is_active == True,
    ).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Delivery staff not found")

    order.delivery_staff_id = data.delivery_staff_id
    db.commit()
    db.refresh(order)

    # Send notification
    notify_order_assigned(order.id, staff.id, staff.name)

    return format_order_response(order)


# ==================== DELIVERY SETTINGS ====================

def _get_or_create_settings(db: Session) -> DeliverySettings:
    """Return the singleton settings row, creating defaults if absent."""
    settings = db.query(DeliverySettings).filter(DeliverySettings.id == 1).first()
    if not settings:
        settings = DeliverySettings(id=1)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.get("/delivery-settings", response_model=DeliverySettingsResponse)
def get_delivery_settings(
    current_user: User = Depends(require_role(["master_admin", "zone_manager"])),
    db: Session = Depends(get_db),
):
    """Get the global delivery charge settings."""
    return _get_or_create_settings(db)


@router.put("/delivery-settings", response_model=DeliverySettingsResponse)
def update_delivery_settings(
    data: DeliverySettingsUpdate,
    current_user: User = Depends(require_role(["master_admin"])),
    db: Session = Depends(get_db),
):
    """Update the global delivery charge settings (master admin only)."""
    settings = _get_or_create_settings(db)
    update_fields = data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(settings, field, value)
    db.commit()
    db.refresh(settings)
    return settings


# ==================== WHATSAPP SETTINGS ====================

def _get_or_create_whatsapp(db: Session) -> WhatsAppSettings:
    """Return singleton WhatsApp settings row, creating with defaults if absent."""
    wa = db.query(WhatsAppSettings).filter(WhatsAppSettings.id == 1).first()
    if not wa:
        wa = WhatsAppSettings(id=1)
        db.add(wa)
        db.commit()
        db.refresh(wa)
    return wa


@router.get("/whatsapp-settings", response_model=WhatsAppSettingsResponse)
def get_whatsapp_settings(
    current_user: User = Depends(require_role(["master_admin"])),
    db: Session = Depends(get_db),
):
    """Get WhatsApp API settings. API key is masked for security."""
    wa = _get_or_create_whatsapp(db)
    return WhatsAppSettingsResponse(
        id=wa.id,
        session_id=wa.session_id,
        # Mask all but last 4 chars
        api_key=('*' * (len(wa.api_key) - 4) + wa.api_key[-4:]) if wa.api_key and len(wa.api_key) > 4 else wa.api_key,
        otp_message_template=wa.otp_message_template or "",
        otp_header=wa.otp_header or "",
        updated_at=wa.updated_at,
        is_configured=bool(wa.session_id and wa.api_key),
    )


@router.put("/whatsapp-settings", response_model=WhatsAppSettingsResponse)
def update_whatsapp_settings(
    data: WhatsAppSettingsUpdate,
    current_user: User = Depends(require_role(["master_admin"])),
    db: Session = Depends(get_db),
):
    """Save WhatsApp API credentials and message template."""
    wa = _get_or_create_whatsapp(db)
    update_fields = data.model_dump(exclude_unset=True)
    # Don't overwrite api_key if client sends back the masked version
    if 'api_key' in update_fields and update_fields['api_key'] and update_fields['api_key'].startswith('*'):
        del update_fields['api_key']
    for field, value in update_fields.items():
        setattr(wa, field, value)
    db.commit()
    db.refresh(wa)
    return WhatsAppSettingsResponse(
        id=wa.id,
        session_id=wa.session_id,
        api_key=('*' * (len(wa.api_key) - 4) + wa.api_key[-4:]) if wa.api_key and len(wa.api_key) > 4 else wa.api_key,
        otp_message_template=wa.otp_message_template or "",
        otp_header=wa.otp_header or "",
        updated_at=wa.updated_at,
        is_configured=bool(wa.session_id and wa.api_key),
    )


@router.post("/whatsapp-settings/test")
def test_whatsapp(
    data: WhatsAppTestRequest,
    current_user: User = Depends(require_role(["master_admin"])),
    db: Session = Depends(get_db),
):
    """Send a test WhatsApp message to verify the integration."""
    wa = _get_or_create_whatsapp(db)
    if not wa.session_id or not wa.api_key:
        raise HTTPException(status_code=400, detail="WhatsApp settings not configured. Save session_id and api_key first.")

    from app.services.otp_service import send_via_whatsapp
    success = send_via_whatsapp(
        phone=data.phone,
        message=data.message or "Test message from FIZZ Delivery.",
        header=wa.otp_header or "FIZZ Delivery",
    )
    if success:
        return {"success": True, "message": f"Test message sent to {data.phone}"}
    raise HTTPException(status_code=502, detail="WhatsApp API call failed. Check your session_id and api_key.")
