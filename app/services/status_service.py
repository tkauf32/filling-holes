from __future__ import annotations

from app.models import Contribution, Pothole, StatusEvent, utcnow
from app.services.estimate_service import generate_estimate_cents

AWAITING_CONFIRMATION = "awaiting_confirmation"
PENDING_FUNDING = "pending_funding"
FUNDED = "funded"
IN_QUEUE_TO_BE_SERVICED = "in_queue_to_be_serviced"
SERVICING = "servicing"
SERVICED = "serviced"
REJECTED = "rejected"
DUPLICATE = "duplicate"

STATUS_LABELS = {
    AWAITING_CONFIRMATION: "Awaiting confirmation",
    PENDING_FUNDING: "Pending funding",
    FUNDED: "Funded",
    IN_QUEUE_TO_BE_SERVICED: "In the queue",
    SERVICING: "Getting filled",
    SERVICED: "Filled",
    REJECTED: "Rejected",
    DUPLICATE: "Duplicate",
}

ADMIN_STATUS_OPTIONS = [
    PENDING_FUNDING,
    FUNDED,
    IN_QUEUE_TO_BE_SERVICED,
    SERVICING,
    SERVICED,
    REJECTED,
    DUPLICATE,
]

_UNSET = object()


def add_status_event(
    pothole: Pothole,
    *,
    to_status: str,
    actor: str,
    note: str | None = None,
    from_status: str | None | object = _UNSET,
) -> StatusEvent:
    resolved_from = pothole.status if from_status is _UNSET else from_status
    return StatusEvent(
        pothole=pothole,
        from_status=resolved_from,
        to_status=to_status,
        actor=actor,
        note=note,
    )


def set_status(pothole: Pothole, to_status: str, actor: str, note: str | None = None) -> StatusEvent:
    previous = pothole.status
    pothole.status = to_status
    pothole.updated_at = utcnow()
    pothole.is_public = to_status not in {AWAITING_CONFIRMATION, REJECTED, DUPLICATE}
    return add_status_event(pothole, to_status=to_status, actor=actor, note=note, from_status=previous)


def confirm_pothole(pothole: Pothole, actor: str = "admin") -> StatusEvent:
    if pothole.estimated_cost_cents is None:
        pothole.estimated_cost_cents = generate_estimate_cents(pothole.severity)
    pothole.funding_goal_cents = pothole.estimated_cost_cents
    pothole.is_public = True
    pothole.confirmed_at = pothole.confirmed_at or utcnow()
    return set_status(
        pothole,
        PENDING_FUNDING,
        actor,
        note="Submission approved and estimate generated.",
    )


def recalculate_top_contributor(pothole: Pothole) -> Contribution | None:
    ordered = sorted(
        pothole.contributions,
        key=lambda contribution: (-contribution.amount_cents, contribution.created_at),
    )
    for contribution in pothole.contributions:
        contribution.is_top_contributor = False

    if not ordered:
        pothole.pothole_name = None
        pothole.name_is_admin_approved = False
        return None

    top = ordered[0]
    top.is_top_contributor = True
    if top.wants_naming_rights and top.suggested_pothole_name:
        pothole.pothole_name = top.suggested_pothole_name.strip()[:120]
        pothole.name_is_admin_approved = False
    return top


def maybe_transition_to_funded(pothole: Pothole) -> StatusEvent | None:
    if (
        pothole.funding_goal_cents
        and pothole.amount_raised_cents >= pothole.funding_goal_cents
        and pothole.status == PENDING_FUNDING
    ):
        return set_status(pothole, FUNDED, "system", note="Funding goal reached.")
    return None
