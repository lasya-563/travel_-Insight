"""JSON API used by the front-end (and usable directly for demos / testing)."""
from flask import Blueprint, current_app, g, jsonify, request, session

from .auth import login_required
from .db import get_db
from .services import analytics, repo

bp = Blueprint("api", __name__, url_prefix="/api")


def _models():
    return current_app.extensions["models"]


@bp.get("/health")
def health():
    get_db().execute("SELECT 1")
    return jsonify(status="ok")


@bp.post("/recommend")
def recommend():
    db = get_db()
    data = request.get_json(silent=True) or {}
    prefs = repo.clean_prefs(data)
    top_n = max(1, min(int(data.get("top_n", 9) or 9), 20))
    rec = _models().recommender(db)
    if rec is None:
        return jsonify(results=[], cold_start=True, segment=None)
    liked = repo.liked_ids(db, g.user["id"] if g.user else None)
    out = rec.recommend(prefs, repo.rating_map(db), liked, top_n)
    seg = _models().segmenter(db)
    out["segment"] = seg.predict(prefs["interests"], prefs["budget"], prefs["trip_days"]) \
        if prefs["interests"] and seg else None
    out["personalised_with_history"] = bool(liked)
    if g.user is None:  # guests keep their last preferences for this browser session
        session["prefs"] = prefs
    return jsonify(out)


@bp.post("/preferences")
@login_required
def save_preferences():
    prefs = repo.clean_prefs(request.get_json(silent=True))
    repo.save_user_prefs(get_db(), g.user["id"], prefs)
    return jsonify(ok=True, prefs=prefs)


@bp.get("/destinations")
def destinations():
    df = repo.destinations_df(get_db())
    q = request.args.get("q", "").strip().lower()
    if q:
        hay = (df["name"] + " " + df["state"] + " " + df["category"] + " " + df["tags"]).str.lower()
        df = df[hay.str.contains(q, regex=False)]
    cols = ["id", "name", "state", "category", "budget_per_day", "rating", "popularity"]
    return jsonify(count=len(df), results=df[cols].head(50).to_dict("records"))


@bp.get("/similar/<int:dest_id>")
def similar(dest_id):
    db = get_db()
    rec = _models().recommender(db)
    return jsonify(results=rec.similar(dest_id, repo.rating_map(db)) if rec else [])


@bp.get("/analytics")
def analytics_data():
    db = get_db()
    return jsonify(analytics.build(db, _models().segmenter(db)))


@bp.post("/destinations/<int:dest_id>/rate")
@login_required
def rate(dest_id):
    db = get_db()
    try:
        value = int((request.get_json(silent=True) or {}).get("rating"))
    except (TypeError, ValueError):
        return jsonify(error="rating must be 1-5"), 400
    if not 1 <= value <= 5:
        return jsonify(error="rating must be 1-5"), 400
    if not repo.get_destination(db, dest_id):
        return jsonify(error="not found"), 404
    db.execute("INSERT INTO ratings(user_id,destination_id,rating) VALUES(?,?,?) "
               "ON CONFLICT(user_id,destination_id) DO UPDATE SET rating=excluded.rating, "
               "created_at=datetime('now')", (g.user["id"], dest_id, value))
    repo.log_interaction(db, g.user["id"], dest_id, "rating", value)
    db.commit()
    d = repo.get_destination(db, dest_id)
    return jsonify(ok=True, rating=d["rating"], user_ratings=d["user_ratings"], mine=value)


@bp.post("/destinations/<int:dest_id>/save")
@login_required
def toggle_save(dest_id):
    db = get_db()
    if not repo.get_destination(db, dest_id):
        return jsonify(error="not found"), 404
    exists = db.execute("SELECT 1 FROM saved WHERE user_id=? AND destination_id=?",
                        (g.user["id"], dest_id)).fetchone()
    if exists:
        db.execute("DELETE FROM saved WHERE user_id=? AND destination_id=?", (g.user["id"], dest_id))
    else:
        db.execute("INSERT INTO saved(user_id,destination_id) VALUES(?,?)", (g.user["id"], dest_id))
        repo.log_interaction(db, g.user["id"], dest_id, "save")
    db.commit()
    return jsonify(ok=True, saved=not exists)
