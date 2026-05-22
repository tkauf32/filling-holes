from __future__ import annotations

from pydantic import BaseModel


class MapPotholeOut(BaseModel):
    public_id: str
    latitude: float
    longitude: float
    status: str
    status_label: str
    severity: str
    severity_label: str
    amount_raised_cents: int
    funding_goal_cents: int | None
    pothole_name: str | None
    thumbnail_url: str | None
    detail_url: str


class NearbyPotholeOut(BaseModel):
    public_id: str
    distance_meters: float
    status: str
    status_label: str
    thumbnail_url: str | None
    detail_url: str
