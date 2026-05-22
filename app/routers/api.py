from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Pothole
from app.schemas import MapPotholeOut, NearbyPotholeOut
from app.services import geo_service
from app.services.estimate_service import SEVERITY_LABELS
from app.services.status_service import STATUS_LABELS

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/potholes", response_model=list[MapPotholeOut])
def pothole_markers(db: Session = Depends(get_db)):
    potholes = (
        db.query(Pothole)
        .options(joinedload(Pothole.images))
        .filter(Pothole.is_public.is_(True))
        .order_by(Pothole.created_at.desc())
        .all()
    )
    return [
        MapPotholeOut(
            public_id=pothole.public_id,
            latitude=pothole.latitude,
            longitude=pothole.longitude,
            status=pothole.status,
            status_label=STATUS_LABELS[pothole.status],
            severity=pothole.severity,
            severity_label=SEVERITY_LABELS[pothole.severity],
            amount_raised_cents=pothole.amount_raised_cents,
            funding_goal_cents=pothole.funding_goal_cents,
            pothole_name=pothole.pothole_name if pothole.name_is_admin_approved else None,
            thumbnail_url=pothole.images[0].url_path if pothole.images else None,
            detail_url=f"/p/{pothole.public_id}",
        )
        for pothole in potholes
    ]


@router.get("/nearby", response_model=list[NearbyPotholeOut])
def nearby_potholes(
    lat: float = Query(...),
    lng: float = Query(...),
    db: Session = Depends(get_db),
):
    matches = geo_service.find_nearby_potholes(db, lat, lng, threshold_meters=50, include_non_public=False)
    return [
        NearbyPotholeOut(
            public_id=pothole.public_id,
            distance_meters=round(distance, 1),
            status=pothole.status,
            status_label=STATUS_LABELS[pothole.status],
            thumbnail_url=pothole.images[0].url_path if pothole.images else None,
            detail_url=f"/p/{pothole.public_id}",
        )
        for pothole, distance in matches
    ]
