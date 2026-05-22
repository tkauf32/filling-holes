from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.utcnow()


class Pothole(Base):
    __tablename__ = "potholes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(64), index=True)
    latitude: Mapped[float]
    longitude: Mapped[float]
    address_hint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(64), default="moderate_pothole")
    estimated_cost_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    funding_goal_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    amount_raised_cents: Mapped[int] = mapped_column(Integer, default=0)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    is_duplicate_of_id: Mapped[int | None] = mapped_column(ForeignKey("potholes.id"), nullable=True)
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    pothole_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    name_is_admin_approved: Mapped[bool] = mapped_column(Boolean, default=False)

    images: Mapped[list["PotholeImage"]] = relationship(
        back_populates="pothole",
        cascade="all, delete-orphan",
        order_by="PotholeImage.sort_order",
    )
    contributions: Mapped[list["Contribution"]] = relationship(
        back_populates="pothole",
        cascade="all, delete-orphan",
        order_by="Contribution.created_at.desc()",
    )
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="pothole",
        cascade="all, delete-orphan",
        order_by="Comment.created_at.desc()",
    )
    status_events: Mapped[list["StatusEvent"]] = relationship(
        back_populates="pothole",
        cascade="all, delete-orphan",
        order_by="StatusEvent.created_at.desc()",
    )
    duplicate_of: Mapped["Pothole | None"] = relationship(remote_side=[id])


class PotholeImage(Base):
    __tablename__ = "pothole_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pothole_id: Mapped[int] = mapped_column(ForeignKey("potholes.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_filename: Mapped[str] = mapped_column(String(255), unique=True)
    url_path: Mapped[str] = mapped_column(String(255))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    pothole: Mapped[Pothole] = relationship(back_populates="images")


class Contribution(Base):
    __tablename__ = "contributions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pothole_id: Mapped[int] = mapped_column(ForeignKey("potholes.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    amount_cents: Mapped[int] = mapped_column(Integer)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=True)
    wants_naming_rights: Mapped[bool] = mapped_column(Boolean, default=False)
    suggested_pothole_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_top_contributor: Mapped[bool] = mapped_column(Boolean, default=False)

    pothole: Mapped[Pothole] = relationship(back_populates="contributions")


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pothole_id: Mapped[int] = mapped_column(ForeignKey("potholes.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    body: Mapped[str] = mapped_column(Text)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False)

    pothole: Mapped[Pothole] = relationship(back_populates="comments")


class StatusEvent(Base):
    __tablename__ = "status_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pothole_id: Mapped[int] = mapped_column(ForeignKey("potholes.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    from_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    to_status: Mapped[str] = mapped_column(String(64))
    actor: Mapped[str] = mapped_column(String(64))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    pothole: Mapped[Pothole] = relationship(back_populates="status_events")
