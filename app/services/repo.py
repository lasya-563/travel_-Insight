"""Database queries shared by views, API and ML code."""
import pandas as pd
from flask import current_app

from ..constants import (ACTIVITIES, BUDGET_MAX, BUDGET_MIN, CATEGORIES, CATEGORY_COLS,
                         join_list, split_list)

DEST_SQL = """
SELECT d.id, d.name, d.state, d.category, d.activities, d.tags, d.budget_per_day,
       d.base_rating, d.best_season, d.description,
       ROUND((d.base_rating * :w + COALESCE(r.s, 0)) / (:w + COALESCE(r.n, 0)), 2) AS rating,
       COALESCE(r.n, 0) AS user_ratings,
       COALESCE(v.n, 0) + 3 * COALESCE(r.n, 0) + 2 * COALESCE(s.n, 0) AS popularity,
       COALESCE(v.n, 0) AS views
FROM destinations d
LEFT JOIN (SELECT destination_id, SUM(rating) s, COUNT(*) n FROM ratings GROUP BY destination_id) r
       ON r.destination_id = d.id
LEFT JOIN (SELECT destination_id, COUNT(*) n FROM saved GROUP BY destination_id) s
       ON s.destination_id = d.id
LEFT JOIN (SELECT destination_id, COUNT(*) n FROM interactions WHERE type='view'
           GROUP BY destination_id) v ON v.destination_id = d.id
"""


def _w():
    return {"w": current_app.config["RATING_PRIOR_WEIGHT"]}


def destinations_df(db) -> pd.DataFrame:
    rows = db.execute(DEST_SQL + " ORDER BY d.id", _w()).fetchall()
    cols = ["id", "name", "state", "category", "activities", "tags", "budget_per_day", "base_rating",
            "best_season", "description", "rating", "user_ratings", "popularity", "views"]
    return pd.DataFrame([tuple(r) for r in rows], columns=cols)


def rating_map(db) -> dict:
    return {r["id"]: r["rating"] for r in db.execute(DEST_SQL, _w()).fetchall()}


def get_destination(db, dest_id):
    row = db.execute(DEST_SQL + " WHERE d.id = :id", {**_w(), "id": dest_id}).fetchone()
    return dict(row) if row else None


def visitors_df(db) -> pd.DataFrame:
    return pd.read_sql_query("SELECT * FROM visitors", db)


def liked_ids(db, user_id):
    if not user_id:
        return []
    rows = db.execute(
        "SELECT destination_id FROM ratings WHERE user_id=? AND rating>=4 "
        "UNION SELECT destination_id FROM saved WHERE user_id=?", (user_id, user_id)).fetchall()
    return [r[0] for r in rows]


# ------------------------------------------------------------------ preferences
def clean_prefs(data: dict) -> dict:
    """Validate and normalise preferences coming from forms / JSON."""
    data = data or {}
    interests = [c for c in data.get("interests", []) if c in CATEGORIES]
    activities = [a for a in data.get("activities", []) if a in ACTIVITIES]
    try:
        budget = int(data.get("budget")) if data.get("budget") not in (None, "") else None
    except (TypeError, ValueError):
        budget = None
    if budget is not None:
        budget = max(BUDGET_MIN, min(BUDGET_MAX, budget))
    try:
        min_rating = max(0.0, min(5.0, float(data.get("min_rating") or 0)))
    except (TypeError, ValueError):
        min_rating = 0.0
    try:
        trip_days = max(1, min(30, int(data.get("trip_days") or 5)))
    except (TypeError, ValueError):
        trip_days = 5
    return {"interests": interests, "activities": activities, "budget": budget,
            "min_rating": min_rating, "trip_days": trip_days,
            "keywords": str(data.get("keywords") or "").strip()[:100]}


def user_prefs(user) -> dict:
    return {"interests": split_list(user["interests"]), "activities": split_list(user["activities"]),
            "budget": user["budget"], "min_rating": user["min_rating"],
            "trip_days": user["trip_days"], "keywords": user["keywords"]}


def save_user_prefs(db, user_id, prefs):
    db.execute(
        "UPDATE users SET interests=?, activities=?, keywords=?, budget=?, min_rating=?, trip_days=? WHERE id=?",
        (join_list(prefs["interests"]), join_list(prefs["activities"]), prefs["keywords"],
         prefs["budget"], prefs["min_rating"], prefs["trip_days"], user_id))
    if prefs["interests"]:  # the user also becomes a visitor record for segmentation
        scores = {CATEGORY_COLS[c]: (4.5 if c in prefs["interests"] else 1.0) for c in CATEGORIES}
        cols = list(scores)
        vals = [scores[c] for c in cols]
        name = db.execute("SELECT name FROM users WHERE id=?", (user_id,)).fetchone()["name"]
        db.execute(
            f"INSERT INTO visitors(name,source,user_id,budget_per_day,trip_days,{','.join(cols)}) "
            f"VALUES(?, 'user', ?, ?, ?, {','.join('?' * len(cols))}) "
            "ON CONFLICT(user_id) DO UPDATE SET budget_per_day=excluded.budget_per_day, "
            "trip_days=excluded.trip_days, " + ", ".join(f"{c}=excluded.{c}" for c in cols),
            (name, user_id, prefs["budget"] or 3500, prefs["trip_days"], *vals))
    db.commit()


# ------------------------------------------------------------------ interactions
def log_interaction(db, user_id, dest_id, kind, value=None):
    db.execute("INSERT INTO interactions(user_id,destination_id,type,value) VALUES(?,?,?,?)",
               (user_id, dest_id, kind, value))
