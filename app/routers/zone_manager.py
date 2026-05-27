from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from typing import List, Optional, Union
from app.database import get_db
from app.dependencies import require_role
from app.models.user import User, UserRole
from app.models.restaurant import Restaurant
from app.models.food_item import FoodItem
from app.models.order import Order, OrderStatus
from app.models.zone import Zone
from app.schemas.restaurant import RestaurantResponse
from app.schemas.food_item import FoodItemResponse
from app.schemas.order import OrderAssign
from app.schemas.user import UserCreate, UserResponse
from app.services.minio_service import upload_image
from app.services.order_service import format_order_response
from app.services.notification_service import notify_order_assigned
from app.utils.security import hash_password
from app.utils.geo import point_in_polygon

router = APIRouter()


@router.get("/restaurants", response_model=List[RestaurantResponse])
def list_zone_restaurants(
    current_user: User = Depends(require_role(["zone_manager"])),
    db: Session = Depends(get_db),
):
    """List restaurants in the zone manager's zone."""
    if not current_user.zone_id:
        raise HTTPException(status_code=400, detail="No zone assigned to this manager")
    return db.query(Restaurant).filter(Restaurant.zone_id == current_user.zone_id).all()


@router.post("/restaurants", response_model=RestaurantResponse)
def create_restaurant_in_zone(
    name: str = Form(...),
    contact: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    images: Union[List[UploadFile], UploadFile, None] = File(default=None),
    current_user: User = Depends(require_role(["zone_manager"])),
    db: Session = Depends(get_db),
):
    """Create a restaurant in the zone manager's zone."""
    if not current_user.zone_id:
        raise HTTPException(status_code=400, detail="No zone assigned to this manager")

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
        zone_id=current_user.zone_id,
        images=image_urls if image_urls else None,
        created_by=current_user.id,
    )
    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)
    return restaurant


@router.post("/restaurants/{restaurant_id}/images")
def add_restaurant_images_zone(
    restaurant_id: int,
    images: Union[List[UploadFile], UploadFile, None] = File(default=None),
    current_user: User = Depends(require_role(["zone_manager"])),
    db: Session = Depends(get_db),
):
    """Add images to a restaurant in the manager's zone."""
    if not current_user.zone_id:
        raise HTTPException(status_code=400, detail="No zone assigned")
    restaurant = db.query(Restaurant).filter(
        Restaurant.id == restaurant_id,
        Restaurant.zone_id == current_user.zone_id,
    ).first()
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


@router.delete("/restaurants/{restaurant_id}/images/{image_index}")
def remove_restaurant_image_zone(
    restaurant_id: int,
    image_index: int,
    current_user: User = Depends(require_role(["zone_manager"])),
    db: Session = Depends(get_db),
):
    """Remove an image from a restaurant in the manager's zone."""
    if not current_user.zone_id:
        raise HTTPException(status_code=400, detail="No zone assigned")
    restaurant = db.query(Restaurant).filter(
        Restaurant.id == restaurant_id,
        Restaurant.zone_id == current_user.zone_id,
    ).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    imgs = list(restaurant.images or [])
    if image_index < 0 or image_index >= len(imgs):
        raise HTTPException(status_code=400, detail="Invalid image index")

    removed_url = imgs.pop(image_index)
    try:
        delete_image(removed_url)
    except Exception:
        pass

    restaurant.images = imgs if imgs else None
    db.commit()
    db.refresh(restaurant)
    return restaurant


@router.post("/restaurants/{restaurant_id}/food-items", response_model=FoodItemResponse)
def create_food_item_in_zone(
    restaurant_id: int,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    price: float = Form(...),
    is_available: bool = Form(True),
    image: Optional[UploadFile] = File(None),
    current_user: User = Depends(require_role(["zone_manager"])),
    db: Session = Depends(get_db),
):
    """Create a food item in a restaurant within the manager's zone."""
    if not current_user.zone_id:
        raise HTTPException(status_code=400, detail="No zone assigned to this manager")

    restaurant = db.query(Restaurant).filter(
        Restaurant.id == restaurant_id,
        Restaurant.zone_id == current_user.zone_id,
    ).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found in your zone")

    image_url = None
    if image:
        image_url = upload_image(image)

    food_item = FoodItem(
        restaurant_id=restaurant_id,
        name=name,
        description=description,
        price=price,
        image_url=image_url,
        is_available=is_available,
    )
    db.add(food_item)
    db.commit()
    db.refresh(food_item)
    return food_item


@router.get("/restaurants/{restaurant_id}/food-items", response_model=List[FoodItemResponse])
def list_food_items_in_zone(
    restaurant_id: int,
    current_user: User = Depends(require_role(["zone_manager"])),
    db: Session = Depends(get_db),
):
    """List food items for a restaurant in the manager's zone."""
    if not current_user.zone_id:
        raise HTTPException(status_code=400, detail="No zone assigned")
    restaurant = db.query(Restaurant).filter(
        Restaurant.id == restaurant_id,
        Restaurant.zone_id == current_user.zone_id,
    ).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found in your zone")
    return db.query(FoodItem).filter(FoodItem.restaurant_id == restaurant_id).all()


@router.put("/food-items/{food_item_id}", response_model=FoodItemResponse)
def update_food_item_in_zone(
    food_item_id: int,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    price: Optional[float] = Form(None),
    is_available: Optional[bool] = Form(None),
    image: Optional[UploadFile] = File(None),
    current_user: User = Depends(require_role(["zone_manager"])),
    db: Session = Depends(get_db),
):
    """Update a food item in the manager's zone."""
    food_item = db.query(FoodItem).filter(FoodItem.id == food_item_id).first()
    if not food_item:
        raise HTTPException(status_code=404, detail="Food item not found")
    # Scope check
    restaurant = db.query(Restaurant).filter(
        Restaurant.id == food_item.restaurant_id,
        Restaurant.zone_id == current_user.zone_id,
    ).first()
    if not restaurant:
        raise HTTPException(status_code=403, detail="Food item not in your zone")

    if name is not None:
        food_item.name = name
    if description is not None:
        food_item.description = description
    if price is not None:
        food_item.price = price
    if is_available is not None:
        food_item.is_available = is_available
    if image:
        try:
            food_item.image_url = upload_image(image)
        except Exception as e:
            print(f"Image upload failed: {e}")

    db.commit()
    db.refresh(food_item)
    return food_item


@router.delete("/food-items/{food_item_id}")
def delete_food_item_in_zone(
    food_item_id: int,
    current_user: User = Depends(require_role(["zone_manager"])),
    db: Session = Depends(get_db),
):
    """Delete a food item in the manager's zone."""
    food_item = db.query(FoodItem).filter(FoodItem.id == food_item_id).first()
    if not food_item:
        raise HTTPException(status_code=404, detail="Food item not found")
    restaurant = db.query(Restaurant).filter(
        Restaurant.id == food_item.restaurant_id,
        Restaurant.zone_id == current_user.zone_id,
    ).first()
    if not restaurant:
        raise HTTPException(status_code=403, detail="Food item not in your zone")

    if food_item.image_url:
        try:
            from app.services.minio_service import delete_image as _del
            _del(food_item.image_url)
        except Exception:
            pass

    db.delete(food_item)
    db.commit()
    return {"message": "Food item deleted"}


@router.get("/orders")
def list_zone_orders(
    current_user: User = Depends(require_role(["zone_manager"])),
    db: Session = Depends(get_db),
):
    """List orders from restaurants in the zone manager's zone."""
    if not current_user.zone_id:
        raise HTTPException(status_code=400, detail="No zone assigned to this manager")

    # Get restaurant IDs in this zone
    zone_restaurants = db.query(Restaurant.id).filter(
        Restaurant.zone_id == current_user.zone_id
    ).all()
    restaurant_ids = [r.id for r in zone_restaurants]

    orders = db.query(Order).filter(
        Order.restaurant_id.in_(restaurant_ids)
    ).order_by(Order.created_at.desc()).all()

    return [format_order_response(order) for order in orders]


@router.post("/orders/{order_id}/assign")
def assign_order_in_zone(
    order_id: int,
    data: OrderAssign,
    current_user: User = Depends(require_role(["zone_manager"])),
    db: Session = Depends(get_db),
):
    """Assign an order to delivery staff (within zone)."""
    if not current_user.zone_id:
        raise HTTPException(status_code=400, detail="No zone assigned to this manager")

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Verify restaurant is in manager's zone
    restaurant = db.query(Restaurant).filter(
        Restaurant.id == order.restaurant_id,
        Restaurant.zone_id == current_user.zone_id,
    ).first()
    if not restaurant:
        raise HTTPException(status_code=403, detail="Order not in your zone")

    staff = db.query(User).filter(
        User.id == data.delivery_staff_id,
        User.role == UserRole.DELIVERY_STAFF,
        User.zone_id == current_user.zone_id,
        User.is_active == True,
    ).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Delivery staff not found")

    order.delivery_staff_id = data.delivery_staff_id
    db.commit()
    db.refresh(order)

    notify_order_assigned(order.id, staff.id, staff.name)
    return format_order_response(order)


# ==================== DELIVERY STAFF ====================

@router.post("/delivery-staff", response_model=UserResponse)
def create_delivery_staff_in_zone(
    data: UserCreate,
    current_user: User = Depends(require_role(["zone_manager"])),
    db: Session = Depends(get_db),
):
    """Create a delivery staff member and auto-assign to zone manager's zone."""
    if not current_user.zone_id:
        raise HTTPException(status_code=400, detail="No zone assigned to this manager")

    existing = db.query(User).filter(
        (User.email == data.email) | (User.phone == data.phone)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email or phone already registered")

    user = User(
        name=data.name,
        email=data.email,
        phone=data.phone,
        password_hash=hash_password(data.password) if data.password else None,
        role=UserRole.DELIVERY_STAFF,
        zone_id=current_user.zone_id,   # auto-assign to manager's zone
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/delivery-staff", response_model=List[UserResponse])
def list_delivery_staff_in_zone(
    current_user: User = Depends(require_role(["zone_manager"])),
    db: Session = Depends(get_db),
):
    """List delivery staff in zone manager's zone."""
    if not current_user.zone_id:
        raise HTTPException(status_code=400, detail="No zone assigned to this manager")
    return db.query(User).filter(
        User.role == UserRole.DELIVERY_STAFF,
        User.zone_id == current_user.zone_id,
        User.is_active == True,
    ).all()


# ==================== CUSTOMERS ====================

@router.get("/customers")
def list_zone_customers(
    current_user: User = Depends(require_role(["zone_manager"])),
    db: Session = Depends(get_db),
):
    """
    List customers whose saved latitude/longitude falls inside this zone.
    Returns customer details enriched with order stats for restaurants in this zone.
    """
    if not current_user.zone_id:
        raise HTTPException(status_code=400, detail="No zone assigned to this manager")

    zone = db.query(Zone).filter(
        Zone.id == current_user.zone_id,
        Zone.is_enabled == True,
    ).first()
    if not zone:
        raise HTTPException(status_code=400, detail="Assigned zone is disabled or not found")

    zone_restaurant_ids = [
        r.id for r in db.query(Restaurant.id)
        .filter(Restaurant.zone_id == current_user.zone_id).all()
    ]

    customers = db.query(User).filter(
        User.role == UserRole.CUSTOMER,
        User.latitude.isnot(None),
        User.longitude.isnot(None),
    ).all()

    result = []
    for user in customers:
        try:
            lat = float(user.latitude)
            lng = float(user.longitude)
        except (TypeError, ValueError):
            continue

        if not point_in_polygon(lat, lng, zone.coordinates):
            continue

        order_query = db.query(Order).filter(Order.customer_id == user.id)
        if zone_restaurant_ids:
            order_query = order_query.filter(Order.restaurant_id.in_(zone_restaurant_ids))

        total_orders = order_query.count()
        total_spent = order_query.with_entities(func.sum(Order.total_amount)).scalar() or 0
        last_order_at = order_query.with_entities(func.max(Order.created_at)).scalar()

        result.append({
            "id": user.id,
            "name": user.name,
            "phone": user.phone,
            "email": user.email,
            "address": user.address,
            "latitude": user.latitude,
            "longitude": user.longitude,
            "is_active": user.is_active,
            "registered_at": user.created_at,
            "total_orders": total_orders,
            "total_spent": round(total_spent or 0, 2),
            "last_order_at": last_order_at,
        })

    result.sort(key=lambda c: c["last_order_at"] or c["registered_at"], reverse=True)
    return result

