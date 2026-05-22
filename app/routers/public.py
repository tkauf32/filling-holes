from __future__ import annotations

from decimal import Decimal, InvalidOperation
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.models import Comment, Contribution, Pothole, PotholeImage
from app.routers import build_context, set_flash, templates
from app.services import geo_service, image_service, notification_service, status_service
from app.services.status_service import AWAITING_CONFIRMATION

router = APIRouter()


def _base_query(db: Session):
    return db.query(Pothole).options(
        joinedload(Pothole.images),
        joinedload(Pothole.contributions),
        joinedload(Pothole.comments),
        joinedload(Pothole.status_events),
    )


def _safe_decimal_to_cents(raw_amount: str) -> int:
    try:
        amount = Decimal(raw_amount)
    except InvalidOperation as exc:
        raise ValueError("Enter a real number for the contribution amount.") from exc
    cents = int(amount * 100)
    if cents <= 0:
        raise ValueError("Contribution amount must be greater than zero.")
    return cents


def _htmx(request: Request) -> bool:
    return request.headers.get("HX-Request", "").lower() == "true"


@router.get("/")
def index(request: Request, db: Session = Depends(get_db)):
    featured = (
        db.query(Pothole)
        .options(joinedload(Pothole.images))
        .filter(Pothole.is_public.is_(True))
        .order_by(Pothole.created_at.desc())
        .limit(3)
        .all()
    )
    total_public = db.query(Pothole).filter(Pothole.is_public.is_(True)).count()
    total_funded = db.query(Pothole).filter(Pothole.status == status_service.FUNDED).count()
    return templates.TemplateResponse(
        "index.html",
        build_context(
            request,
            page_title="Report a hole. Fund a fix. Claim the glory.",
            featured_potholes=featured,
            total_public=total_public,
            total_funded=total_funded,
        ),
    )


@router.get("/map")
def map_page(request: Request):
    return templates.TemplateResponse(
        "map.html",
        build_context(request, page_title="Chicago pothole map"),
    )


@router.get("/submit")
def submit_page(request: Request):
    return templates.TemplateResponse(
        "submit.html",
        build_context(
            request,
            page_title="Report a hole",
            form_data={},
            nearby_matches=[],
            error_message=None,
        ),
    )


@router.post("/submit")
async def create_submission(
    request: Request,
    severity: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    description: str | None = Form(default=None),
    address_hint: str | None = Form(default=None),
    duplicate_override: str | None = Form(default=None),
    images: list[UploadFile] | None = File(default=None),
    db: Session = Depends(get_db),
):
    form_data = {
        "severity": severity,
        "latitude": latitude,
        "longitude": longitude,
        "description": description or "",
        "address_hint": address_hint or "",
        "duplicate_override": duplicate_override or "",
    }

    if settings.chicago_only and not geo_service.is_chicago_location(latitude, longitude):
        return templates.TemplateResponse(
            "submit.html",
            build_context(
                request,
                page_title="Report a hole",
                form_data=form_data,
                nearby_matches=[],
                error_message="Right now we’re only filling holes in Chicago. Your hole may be valid, but it’s outside our current zone.",
            ),
            status_code=400,
        )

    nearby_matches = geo_service.find_nearby_potholes(db, latitude, longitude, include_non_public=False)
    if nearby_matches and duplicate_override != "yes":
        return templates.TemplateResponse(
            "submit.html",
            build_context(
                request,
                page_title="Report a hole",
                form_data=form_data,
                nearby_matches=nearby_matches,
                error_message="Looks like someone may have already found this hole.",
            ),
            status_code=400,
        )

    try:
        processed_images = await image_service.process_uploads(images or [])
    except image_service.ImageValidationError as exc:
        return templates.TemplateResponse(
            "submit.html",
            build_context(
                request,
                page_title="Report a hole",
                form_data=form_data,
                nearby_matches=[],
                error_message=str(exc),
            ),
            status_code=400,
        )

    pothole = Pothole(
        public_id=uuid4().hex[:10],
        status=AWAITING_CONFIRMATION,
        latitude=latitude,
        longitude=longitude,
        address_hint=address_hint or None,
        description=description or None,
        severity=severity,
        is_public=False,
    )
    db.add(pothole)
    db.flush()

    db.add(
        status_service.add_status_event(
            pothole,
            to_status=AWAITING_CONFIRMATION,
            actor="public",
            note="Pothole submitted for review.",
            from_status=None,
        )
    )

    for image in processed_images:
        db.add(
            PotholeImage(
                pothole_id=pothole.id,
                original_filename=image.original_filename,
                stored_filename=image.stored_filename,
                url_path=image.url_path,
                sort_order=image.sort_order,
            )
        )

    db.commit()
    db.refresh(pothole)
    notification_service.notify_admin_new_submission(pothole)
    return RedirectResponse(url=f"/submit/success/{pothole.public_id}", status_code=303)


@router.get("/submit/success/{public_id}")
def submit_success(public_id: str, request: Request, db: Session = Depends(get_db)):
    pothole = db.query(Pothole).filter(Pothole.public_id == public_id).first()
    if not pothole:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        "submit_success.html",
        build_context(request, page_title="Submission received", pothole=pothole),
    )


@router.get("/p/{public_id}")
def pothole_detail(public_id: str, request: Request, db: Session = Depends(get_db)):
    pothole = (
        _base_query(db)
        .filter(Pothole.public_id == public_id, Pothole.is_public.is_(True))
        .first()
    )
    if not pothole:
        raise HTTPException(status_code=404)

    share_url = f"{settings.app_base_url}/p/{public_id}"
    visible_comments = [comment for comment in pothole.comments if not comment.is_hidden]
    top_contributor = next((c for c in pothole.contributions if c.is_top_contributor), None)
    return templates.TemplateResponse(
        "pothole_detail.html",
        build_context(
            request,
            page_title=f"Pothole {public_id}",
            pothole=pothole,
            visible_comments=visible_comments,
            top_contributor=top_contributor,
            share_url=share_url,
            contribution_error=None,
            comment_error=None,
        ),
    )


@router.post("/p/{public_id}/contribute")
async def contribute(
    public_id: str,
    request: Request,
    amount: str = Form(...),
    display_name: str | None = Form(default=None),
    is_anonymous: str | None = Form(default="on"),
    wants_naming_rights: str | None = Form(default=None),
    suggested_pothole_name: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    pothole = (
        _base_query(db)
        .filter(Pothole.public_id == public_id, Pothole.is_public.is_(True))
        .first()
    )
    if not pothole:
        raise HTTPException(status_code=404)

    try:
        amount_cents = _safe_decimal_to_cents(amount)
    except ValueError as exc:
        context = build_context(
            request,
            pothole=pothole,
            visible_comments=[comment for comment in pothole.comments if not comment.is_hidden],
            top_contributor=next((c for c in pothole.contributions if c.is_top_contributor), None),
            contribution_error=str(exc),
            comment_error=None,
            share_url=f"{settings.app_base_url}/p/{public_id}",
        )
        template = "partials/contribution_form.html" if _htmx(request) else "pothole_detail.html"
        return templates.TemplateResponse(template, context, status_code=400)

    contribution = Contribution(
        pothole=pothole,
        amount_cents=amount_cents,
        display_name=(display_name or "").strip() or None,
        is_anonymous=is_anonymous == "on",
        wants_naming_rights=wants_naming_rights == "on",
        suggested_pothole_name=(suggested_pothole_name or "").strip() or None,
    )
    db.add(contribution)

    pothole.amount_raised_cents += amount_cents
    status_service.recalculate_top_contributor(pothole)
    funded_event = status_service.maybe_transition_to_funded(pothole)
    if funded_event:
        db.add(funded_event)
    db.commit()
    pothole = (
        _base_query(db)
        .filter(Pothole.public_id == public_id, Pothole.is_public.is_(True))
        .first()
    )

    if _htmx(request):
        return templates.TemplateResponse(
            "partials/contribution_form.html",
            build_context(
                request,
                pothole=pothole,
                top_contributor=next((c for c in pothole.contributions if c.is_top_contributor), None),
                contribution_error=None,
            ),
        )

    set_flash(request, "Fake contribution accepted. No card required, just civic theater.", "success")
    return RedirectResponse(url=f"/p/{public_id}", status_code=303)


@router.post("/p/{public_id}/comment")
async def add_comment(
    public_id: str,
    request: Request,
    display_name: str | None = Form(default=None),
    body: str = Form(...),
    db: Session = Depends(get_db),
):
    pothole = (
        _base_query(db)
        .filter(Pothole.public_id == public_id, Pothole.is_public.is_(True))
        .first()
    )
    if not pothole:
        raise HTTPException(status_code=404)

    cleaned_body = body.strip()
    if not cleaned_body:
        context = build_context(
            request,
            pothole=pothole,
            visible_comments=[comment for comment in pothole.comments if not comment.is_hidden],
            comment_error="Comment text cannot be empty.",
        )
        template = "partials/comments.html" if _htmx(request) else "pothole_detail.html"
        return templates.TemplateResponse(template, context, status_code=400)

    db.add(
        Comment(
            pothole=pothole,
            display_name=(display_name or "").strip() or None,
            body=cleaned_body,
        )
    )
    db.commit()
    pothole = (
        _base_query(db)
        .filter(Pothole.public_id == public_id, Pothole.is_public.is_(True))
        .first()
    )

    visible_comments = [comment for comment in pothole.comments if not comment.is_hidden]
    if _htmx(request):
        return templates.TemplateResponse(
            "partials/comments.html",
            build_context(request, pothole=pothole, visible_comments=visible_comments, comment_error=None),
        )

    set_flash(request, "Comment posted. Chicago has been informed.", "success")
    return RedirectResponse(url=f"/p/{public_id}", status_code=303)
