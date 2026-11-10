"""Shared vocabularies and helpers used by the ML code, the DB layer and the UI."""
import re

CATEGORIES = [
    "Heritage", "Spiritual", "Beach", "Nature",
    "Hill Station", "Adventure", "Wildlife", "City",
]

ACTIVITIES = [
    "trekking", "camping", "photography", "sightseeing", "boating",
    "temple visits", "safari", "birdwatching", "water sports", "rafting",
    "paragliding", "skiing", "shopping", "food tours", "yoga & meditation",
    "scuba diving", "cycling", "heritage walks", "stargazing", "museums",
    "nightlife",
]

CATEGORY_ICONS = {
    "Heritage": "🏰", "Spiritual": "🛕", "Beach": "🏖️", "Nature": "🌿",
    "Hill Station": "⛰️", "Adventure": "🧗", "Wildlife": "🐅", "City": "🏙️",
}

CATEGORY_COLORS = {
    "Heritage": "#c2410c", "Spiritual": "#a16207", "Beach": "#0891b2",
    "Nature": "#15803d", "Hill Station": "#4f46e5", "Adventure": "#dc2626",
    "Wildlife": "#65a30d", "City": "#475569",
}

# budget per person per day, INR
BUDGET_MIN, BUDGET_MAX = 500, 20000
BUDGET_BANDS = [("Budget (< ₹2,500)", 0, 2500), ("Mid-range (₹2,500–4,500)", 2500, 4500),
                ("Premium (> ₹4,500)", 4500, 10**9)]


def tok(text: str) -> str:
    """'Hill Station' -> 'hill_station', 'yoga & meditation' -> 'yoga_meditation'."""
    return re.sub(r"[^a-z0-9]+", "_", str(text).lower()).strip("_")


CATEGORY_COLS = {c: tok(c) for c in CATEGORIES}  # also the `visitors` column names


def split_list(value) -> list:
    if not value:
        return []
    return [p.strip() for p in str(value).split(";") if p.strip()]


def join_list(items) -> str:
    return ";".join(i.strip() for i in items if i and i.strip())
