"""Shared constants for the Iris Core application."""

# Mapping of patient phrasing to formal barrier categories
BARRIER_KEYWORDS: dict[str, str] = {
    "can't afford": "cost barrier",
    "too expensive": "cost barrier",
    "cost": "cost barrier",
    "no insurance": "insurance barrier",
    "pharmacy too far": "pharmacy access barrier",
    "far away": "pharmacy access barrier",
    "no ride": "transportation barrier",
    "no car": "transportation barrier",
    "transportation": "transportation barrier",
    "can't get to": "access barrier",
    "don't understand": "health literacy barrier",
    "confusing": "health literacy barrier",
    "side effect": "side effect concern",
    "makes me dizzy": "side effect concern",
    "makes me tired": "side effect concern",
    "makes me sick": "side effect concern",
}

# Keywords indicating poor adherence or missed doses
ADHERENCE_KEYWORDS: list[str] = [
    "skipping", "stopped taking", "not taking", "ran out",
    "forgot", "missed", "don't take", "haven't been taking",
]
