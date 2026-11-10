"""Server-rendered pages."""
import math

from flask import (Blueprint, abort, current_app, g, redirect, render_template, request, session, url_for)

from .auth import login_required
from .constants import BUDGET_MAX, BUDGET_MIN, CATEGORIES
from .db import get_db
from .services import repo

bp = Blueprint("views", __name__)
PAGE_SIZE = 12


def models():
    return current_app.extensions["models"]


def current_prefs() -> dict:
    if g.user is not None:
        return repo.user_prefs(g.user)
    return repo.clean_prefs(session.get("prefs", {}))


@bp.route("/")
def home():
    df = repo.destinations_df(get_db())
    featured = df.sort_values(["popularity", "rating"], ascending=False).head(8).to_dict("records")
    stats = {"destinations": len(df), "categories": df["category"].nunique(),
             "states": df["state"].nunique()}
    return render_template("home.html", featured=featured, stats=stats)


@bp.route("/explore")
def explore():
    df = repo.destinations_df(get_db())
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "")
    state = request.args.get("state", "")
    sort = request.args.get("sort", "popularity")
    try:
        max_budget = int(request.args.get("max_budget", "") or 0)
    except ValueError:
        max_budget = 0

    states = sorted(df["state"].unique())
    if q:
        hay = (df["name"] + " " + df["state"] + " " + df["category"] + " " + df["activities"] + " "
               + df["tags"] + " " + df["description"]).str.lower()
        for term in q.lower().split():
            df = df[hay.loc[df.index].str.contains(term, regex=False)]
    if category in CATEGORIES:
        df = df[df["category"] == category]
    if state:
        df = df[df["state"] == state]
    if max_budget:
        df = df[df["budget_per_day"] <= max_budget]
    order = {"rating": ("rating", False), "budget": ("budget_per_day", True),
             "name": ("name", True), "popularity": ("popularity", False)}
    col, asc = order.get(sort, order["popularity"])
    df = df.sort_values(col, ascending=asc)

    total = len(df)
    pages = max(1, math.ceil(total / PAGE_SIZE))
    page = min(max(request.args.get("page", 1, type=int), 1), pages)
    items = df.iloc[(page - 1) * PAGE_SIZE: page * PAGE_SIZE].to_dict("records")
    args = {k: v for k, v in request.args.items() if k != "page" and v}
    return render_template("explore.html", items=items, total=total, page=page, pages=pages,
                           states=states, q=q, category=category, state=state, sort=sort,
                           max_budget=max_budget or "", args=args)


@bp.route("/destination/<int:dest_id>")
def destination(dest_id):
    db = get_db()
    dest = repo.get_destination(db, dest_id)
    if not dest:
        abort(404)
    seen = session.get("seen", [])
    if dest_id not in seen:  # count one view per session so refreshes don't inflate popularity
        repo.log_interaction(db, g.user["id"] if g.user else None, dest_id, "view")
        db.commit()
        session["seen"] = (seen + [dest_id])[-60:]
    my_rating, is_saved = None, False
    if g.user:
        r = db.execute("SELECT rating FROM ratings WHERE user_id=? AND destination_id=?",
                       (g.user["id"], dest_id)).fetchone()
        my_rating = r["rating"] if r else None
        is_saved = bool(db.execute("SELECT 1 FROM saved WHERE user_id=? AND destination_id=?",
                                   (g.user["id"], dest_id)).fetchone())
    rec = models().recommender(db)
    similar = rec.similar(dest_id, repo.rating_map(db)) if rec else []
    return render_template("destination.html", d=dest, my_rating=my_rating, is_saved=is_saved,
                           similar=similar)


@bp.route("/recommendations")
def recommendations():
    return render_template("recommend.html", prefs=current_prefs(),
                           budget_min=BUDGET_MIN, budget_max=BUDGET_MAX)


@bp.route("/preferences")
def preferences():
    return redirect(url_for("views.recommendations"))


@bp.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@bp.route("/profile")
@login_required
def profile():
    db = get_db()
    uid = g.user["id"]
    prefs = repo.user_prefs(g.user)
    seg = models().segmenter(db)
    segment = seg.predict(prefs["interests"], prefs["budget"], prefs["trip_days"]) \
        if prefs["interests"] and seg else None
    saved = db.execute("SELECT d.id, d.name, d.category, d.state FROM saved s JOIN destinations d "
                       "ON d.id=s.destination_id WHERE s.user_id=? ORDER BY s.created_at DESC", (uid,)).fetchall()
    rated = db.execute("SELECT d.id, d.name, r.rating FROM ratings r JOIN destinations d "
                       "ON d.id=r.destination_id WHERE r.user_id=? ORDER BY r.created_at DESC", (uid,)).fetchall()
    return render_template("profile.html", prefs=prefs, segment=segment, saved=saved, rated=rated)
