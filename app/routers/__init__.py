from __future__ import annotations

from datetime import datetime

from fastapi.templating import Jinja2Templates

from app.config import settings
from app.services.estimate_service import SEVERITY_LABELS
from app.services.status_service import STATUS_LABELS

templates = Jinja2Templates(directory="app/templates")


def format_money(cents: int | None) -> str:
    if cents is None:
        return "TBD"
    return f"${cents / 100:,.0f}"


templates.env.filters["money"] = format_money
templates.env.globals["status_labels"] = STATUS_LABELS
templates.env.globals["severity_labels"] = SEVERITY_LABELS
templates.env.globals["settings"] = settings


def set_flash(request, message: str, kind: str = "info") -> None:
    request.session["flash"] = {"message": message, "kind": kind}


def build_context(request, **kwargs):
    flash = request.session.pop("flash", None) if hasattr(request, "session") else None
    context = {
        "request": request,
        "flash": flash,
        "status_labels": STATUS_LABELS,
        "severity_labels": SEVERITY_LABELS,
        "current_year": datetime.utcnow().year,
    }
    context.update(kwargs)
    return context
