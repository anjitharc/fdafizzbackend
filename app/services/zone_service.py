from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.zone import Zone
from app.models.restaurant import Restaurant
from app.utils.geo import point_in_polygon


def get_zone_for_point(db: Session, lat: float, lng: float) -> Optional[Zone]:
    """Find which zone a point belongs to."""
    zones = db.query(Zone).filter(Zone.is_enabled == True).all()
    for zone in zones:
        if point_in_polygon(lat, lng, zone.coordinates):
            return zone
    return None


def get_restaurants_in_zone(db: Session, zone_id: int) -> List[Restaurant]:
    """Get all active restaurants in a zone."""
    zone = db.query(Zone).filter(
        Zone.id == zone_id,
        Zone.is_enabled == True,
    ).first()
    if not zone:
        return []
    return db.query(Restaurant).filter(
        Restaurant.zone_id == zone_id,
        Restaurant.is_active == 1,
    ).all()


def get_restaurants_for_customer_location(db: Session, lat: float, lng: float) -> List[Restaurant]:
    """Get restaurants visible to a customer based on their location."""
    zone = get_zone_for_point(db, lat, lng)
    if zone is None:
        return []
    return get_restaurants_in_zone(db, zone.id)
