from __future__ import annotations

from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.models import Comment, Pothole
from app.routers import build_context, set_flash, templates
from app.services import status_service

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(request: Request):
    if not request.session.get("is_admin"):
        raise HTTPException(status_code=303, headers={"Location": "/admin/login"})


def _pothole_query(db: Session):
    return db.query(Pothole).options(
        joinedload(Pothole.images),
        joinedload(Pothole.contributions),
        joinedload(Pothole.comments),
        joinedload(Pothole.status_events),
        joinedload(Pothole.duplicate_of),
    )


@router.get("")
def admin_home(request: Request, status: str | None = None, db: Session = Depends(get_db)):
    if not request.session.get("is_admin"):
        return RedirectResponse(url="/admin/login", status_code=303)

    pothole_query = _pothole_query(db).order_by(Pothole.created_at.desc())
    potholes = pothole_query.filter(Pothole.status == status).all() if status else pothole_query.all()
    counts = {
        key: db.query(Pothole).filter(Pothole.status == key).count()
        for key in status_service.STATUS_LABELS
    }

    return templates.TemplateResponse(
        "admin_dashboard.html",
        build_context(
            request,
            page_title="Admin dashboard",
            potholes=potholes,
            counts=counts,
            active_status=status,
            status_options=status_service.ADMIN_STATUS_OPTIONS,
        ),
    )


@router.get("/login")
def admin_login(request: Request):
    return templates.TemplateResponse(
        "admin_login.html",
        build_context(request, page_title="Admin login", error_message=None),
    )


@router.post("/login")
def admin_login_submit(request: Request, password: str = Form(...)):
    if password != settings.admin_password:
        return templates.TemplateResponse(
            "admin_login.html",
            build_context(
                request,
                page_title="Admin login",
                error_message="That password did not survive review.",
            ),
            status_code=400,
        )

    request.session["is_admin"] = True
    set_flash(request, "Admin session active.", "success")
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/logout")
def admin_logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/admin/login", status_code=303)


@router.get("/potholes/{pothole_id}")
def admin_pothole_detail(pothole_id: int, request: Request, db: Session = Depends(get_db)):
    _require_admin(request)
    pothole = _pothole_query(db).filter(Pothole.id == pothole_id).first()
    if not pothole:
        raise HTTPException(status_code=404)

    visible_candidates = (
        db.query(Pothole)
        .filter(Pothole.id != pothole.id, Pothole.is_public.is_(True))
        .order_by(Pothole.created_at.desc())
        .limit(15)
        .all()
    )
    return templates.TemplateResponse(
        "admin_pothole_detail.html",
        build_context(
            request,
            page_title=f"Admin pothole {pothole.public_id}",
            pothole=pothole,
            duplicate_candidates=visible_candidates,
            status_options=status_service.ADMIN_STATUS_OPTIONS,
        ),
    )


@router.post("/potholes/{pothole_id}/confirm")
def confirm_pothole(pothole_id: int, request: Request, db: Session = Depends(get_db)):
    _require_admin(request)
    pothole = _pothole_query(db).filter(Pothole.id == pothole_id).first()
    if not pothole:
        raise HTTPException(status_code=404)

    event = status_service.confirm_pothole(pothole)
    db.add(event)
    db.commit()
    set_flash(request, "Pothole confirmed and estimate generated.", "success")
    return RedirectResponse(url=f"/admin/potholes/{pothole.id}", status_code=303)


def _parse_money_to_cents(raw: str) -> int:
    try:
        return int(Decimal(raw) * 100)
    except InvalidOperation as exc:
        raise ValueError("Enter a valid dollar amount.") from exc


@router.post("/potholes/{pothole_id}/status")
def update_status(
    pothole_id: int,
    request: Request,
    status: str = Form(...),
    admin_notes: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    _require_admin(request)
    pothole = _pothole_query(db).filter(Pothole.id == pothole_id).first()
    if not pothole:
        raise HTTPException(status_code=404)
    if status not in status_service.ADMIN_STATUS_OPTIONS:
        raise HTTPException(status_code=400, detail="Invalid status")

    pothole.admin_notes = (admin_notes or "").strip() or pothole.admin_notes
    event = status_service.set_status(pothole, status, "admin", note="Manual admin override.")
    db.add(event)
    db.commit()
    set_flash(request, f"Status updated to {status_service.STATUS_LABELS[status]}.", "success")
    return RedirectResponse(url=f"/admin/potholes/{pothole.id}", status_code=303)


@router.post("/potholes/{pothole_id}/estimate")
def update_estimate(
    pothole_id: int,
    request: Request,
    estimate_amount: str = Form(...),
    db: Session = Depends(get_db),
):
    _require_admin(request)
    pothole = _pothole_query(db).filter(Pothole.id == pothole_id).first()
    if not pothole:
        raise HTTPException(status_code=404)

    try:
        estimate_cents = _parse_money_to_cents(estimate_amount)
    except ValueError as exc:
        set_flash(request, str(exc), "error")
        return RedirectResponse(url=f"/admin/potholes/{pothole.id}", status_code=303)

    pothole.estimated_cost_cents = estimate_cents
    pothole.funding_goal_cents = estimate_cents
    db.commit()
    set_flash(request, "Estimate updated.", "success")
    return RedirectResponse(url=f"/admin/potholes/{pothole.id}", status_code=303)


@router.post("/potholes/{pothole_id}/reject")
def reject_pothole(
    pothole_id: int,
    request: Request,
    admin_notes: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    _require_admin(request)
    pothole = _pothole_query(db).filter(Pothole.id == pothole_id).first()
    if not pothole:
        raise HTTPException(status_code=404)

    pothole.admin_notes = (admin_notes or "").strip() or pothole.admin_notes
    event = status_service.set_status(pothole, status_service.REJECTED, "admin", note="Rejected by admin.")
    db.add(event)
    db.commit()
    set_flash(request, "Submission rejected.", "success")
    return RedirectResponse(url=f"/admin/potholes/{pothole.id}", status_code=303)


@router.post("/potholes/{pothole_id}/duplicate")
def mark_duplicate(
    pothole_id: int,
    request: Request,
    duplicate_of_id: int | None = Form(default=None),
    admin_notes: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    _require_admin(request)
    pothole = _pothole_query(db).filter(Pothole.id == pothole_id).first()
    if not pothole:
        raise HTTPException(status_code=404)

    pothole.is_duplicate_of_id = duplicate_of_id
    pothole.admin_notes = (admin_notes or "").strip() or pothole.admin_notes
    event = status_service.set_status(pothole, status_service.DUPLICATE, "admin", note="Marked as duplicate.")
    db.add(event)
    db.commit()
    set_flash(request, "Submission marked as duplicate.", "success")
    return RedirectResponse(url=f"/admin/potholes/{pothole.id}", status_code=303)


@router.post("/comments/{comment_id}/hide")
def hide_comment(comment_id: int, request: Request, db: Session = Depends(get_db)):
    _require_admin(request)
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404)
    comment.is_hidden = True
    db.commit()
    set_flash(request, "Comment hidden.", "success")
    return RedirectResponse(url=f"/admin/potholes/{comment.pothole_id}", status_code=303)


@router.post("/comments/{comment_id}/unhide")
def unhide_comment(comment_id: int, request: Request, db: Session = Depends(get_db)):
    _require_admin(request)
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404)
    comment.is_hidden = False
    db.commit()
    set_flash(request, "Comment restored.", "success")
    return RedirectResponse(url=f"/admin/potholes/{comment.pothole_id}", status_code=303)
