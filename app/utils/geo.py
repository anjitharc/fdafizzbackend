from shapely.geometry import Point, Polygon
from typing import List, Dict, Optional


def point_in_polygon(lat: float, lng: float, coordinates: List[Dict[str, float]]) -> bool:
    """Check if a point (lat, lng) is inside a polygon defined by coordinates."""
    if not coordinates or len(coordinates) < 3:
        return False

    # Create polygon from coordinates list [{lat: x, lng: y}, ...]
    polygon_points = [(coord["lng"], coord["lat"]) for coord in coordinates]
    polygon = Polygon(polygon_points)
    point = Point(lng, lat)

    return polygon.contains(point)


def find_zone_for_point(lat: float, lng: float, zones: list) -> Optional[int]:
    """Given a point, find which zone it belongs to. Returns zone_id or None."""
    for zone in zones:
        if point_in_polygon(lat, lng, zone.coordinates):
            return zone.id
    return None
