from __future__ import annotations

import math

from sqlalchemy.orm import Session

from app.models import Pothole
from app.services.status_service import DUPLICATE, REJECTED

CHICAGO_BOUNDS = {
    "lat_min": 41.60,
    "lat_max": 42.05,
    "lng_min": -87.95,
    "lng_max": -87.50,
}


def is_chicago_location(latitude: float, longitude: float) -> bool:
    return (
        CHICAGO_BOUNDS["lat_min"] <= latitude <= CHICAGO_BOUNDS["lat_max"]
        and CHICAGO_BOUNDS["lng_min"] <= longitude <= CHICAGO_BOUNDS["lng_max"]
    )


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6_371_000
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c


def find_nearby_potholes(
    db: Session,
    latitude: float,
    longitude: float,
    *,
    threshold_meters: float = 50,
    include_non_public: bool = False,
) -> list[tuple[Pothole, float]]:
    query = db.query(Pothole)
    if include_non_public:
        query = query.filter(Pothole.status.notin_([REJECTED, DUPLICATE]))
    else:
        query = query.filter(Pothole.is_public.is_(True))

    matches: list[tuple[Pothole, float]] = []
    for pothole in query.all():
        distance = haversine_meters(latitude, longitude, pothole.latitude, pothole.longitude)
        if distance <= threshold_meters:
            matches.append((pothole, distance))

    matches.sort(key=lambda item: item[1])
    return matches
