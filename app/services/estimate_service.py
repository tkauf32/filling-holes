from __future__ import annotations

import random

SEVERITY_RANGES = {
    "small_crack": (800, 1100),
    "moderate_pothole": (1000, 1400),
    "suspension_destroyer": (1300, 1700),
    "small_child_could_disappear": (1600, 2000),
}

SEVERITY_LABELS = {
    "small_crack": "Small crack",
    "moderate_pothole": "Moderate pothole",
    "suspension_destroyer": "Suspension destroyer",
    "small_child_could_disappear": "Small child could disappear",
}


def generate_estimate_cents(severity: str) -> int:
    low, high = SEVERITY_RANGES.get(severity, (800, 2000))
    return random.randint(low, high)
