"""Admin / data-maintainer screens: destination CRUD, CSV import, model retraining."""
import csv
import io

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from .auth import admin_required
from .constants import ACTIVITIES, CATEGORIES, join_list, split_list
from .db import bump_meta, get_db
from .services import repo

bp = Blueprint("admin", __name__, url_prefix="/admin")


def _parse(form):
    """Validate destination form/CSV fields. Returns (values, error)."""
    name = form.get("name", "").strip()
    state = form.get("state", "").strip()
    category = form.get("category", "").strip()
    acts = [a for a in split_list(form.get("activities", "").replace(",", ";")) if a in ACTIVITIES]
    tags = join_list(split_list(form.get("tags", "").replace(",", ";")))
    try:
        budget = int(form.get("budget_per_day"))
        rating = float(form.get("rating"))
    except (TypeError, ValueError):
        return None, "Budget and rating must be numbers."
    if not name or not state:
        return None, "Name and state are required."
    if category not in CATEGORIES:
        return None, f"Category must be one of: {', '.join(CATEGORIES)}."
    if not acts:
        return None, "Pick at least one valid activity."
    if not 100 <= budget <= 100000:
        return None, "Budget per day must be between 100 and 100000."
    if not 1 <= rating <= 5:
        return None, "Rating must be between 1 and 5."
    return {"name": name, "state": state, "category": category, "activities": join_list(acts),
            "tags": tags, "budget_per_day": budget, "base_rating": rating,
            "best_season": form.get("best_season", "").strip()[:40],
            "description": form.get("description", "").strip()[:600]}, None


def _changed(db):
    bump_meta(db, "rec_version")
    db.commit()


@bp.route("/")
@admin_required
def index():
    df = repo.destinations_df(get_db())
    return render_template("admin/index.html", items=df.sort_values("name").to_dict("records"))


@bp.route("/destination/new", methods=["GET", "POST"])
@bp.route("/destination/<int:dest_id>/edit", methods=["GET", "POST"])
@admin_required
def edit(dest_id=None):
    db = get_db()
    existing = db.execute("SELECT * FROM destinations WHERE id=?", (dest_id,)).fetchone() if dest_id else None
    if dest_id and not existing:
        abort(404)
    if request.method == "POST":
        form = request.form.to_dict()
        form["activities"] = join_list(request.form.getlist("activities"))
        values, error = _parse({**form, "rating": form.get("rating")})
        if error:
            flash(error, "error")
            return render_template("admin/form.html", d=form, new=not dest_id), 400
        try:
            if dest_id:
                db.execute("UPDATE destinations SET name=?,state=?,category=?,activities=?,tags=?,"
                           "budget_per_day=?,base_rating=?,best_season=?,description=? WHERE id=?",
                           (*values.values(), dest_id))
            else:
                db.execute("INSERT INTO destinations(name,state,category,activities,tags,budget_per_day,"
                           "base_rating,best_season,description) VALUES(?,?,?,?,?,?,?,?,?)",
                           tuple(values.values()))
        except Exception:
            db.rollback()
            flash("A destination with that name already exists.", "error")
            return render_template("admin/form.html", d=form, new=not dest_id), 400
        _changed(db)
        flash("Destination saved. Recommendation model refreshed.", "ok")
        return redirect(url_for("admin.index"))
    d = dict(existing, rating=existing["base_rating"]) if existing else {"rating": 4.0, "budget_per_day": 3000}
    return render_template("admin/form.html", d=d, new=not dest_id)


@bp.post("/destination/<int:dest_id>/delete")
@admin_required
def delete(dest_id):
    db = get_db()
    db.execute("DELETE FROM destinations WHERE id=?", (dest_id,))
    _changed(db)
    flash("Destination deleted.", "ok")
    return redirect(url_for("admin.index"))


@bp.post("/import")
@admin_required
def import_csv():
    file = request.files.get("file")
    if not file or not file.filename.lower().endswith(".csv"):
        flash("Please choose a .csv file.", "error")
        return redirect(url_for("admin.index"))
    try:
        reader = csv.DictReader(io.StringIO(file.read().decode("utf-8-sig")))
        required = {"name", "state", "category", "activities", "budget_per_day", "rating"}
        if not required <= set(reader.fieldnames or []):
            raise ValueError(f"CSV needs columns: {', '.join(sorted(required))} (+ tags, best_season, description)")
        db, added, updated, skipped = get_db(), 0, 0, 0
        for row in reader:
            values, err = _parse({**row, "budget_per_day": row.get("budget_per_day"), "rating": row.get("rating")})
            if err:
                skipped += 1
                continue
            cur = db.execute("UPDATE destinations SET state=?,category=?,activities=?,tags=?,budget_per_day=?,"
                             "base_rating=?,best_season=?,description=? WHERE name=?",
                             (*list(values.values())[1:], values["name"]))
            if cur.rowcount:
                updated += 1
            else:
                db.execute("INSERT INTO destinations(name,state,category,activities,tags,budget_per_day,"
                           "base_rating,best_season,description) VALUES(?,?,?,?,?,?,?,?,?)",
                           tuple(values.values()))
                added += 1
        _changed(db)
        flash(f"Import finished: {added} added, {updated} updated, {skipped} skipped (invalid rows).", "ok")
    except (ValueError, UnicodeDecodeError, csv.Error) as exc:
        flash(f"Import failed: {exc}", "error")
    return redirect(url_for("admin.index"))


@bp.post("/retrain")
@admin_required
def retrain():
    db = get_db()
    bump_meta(db, "seg_version")
    bump_meta(db, "rec_version")
    db.commit()
    flash("Models will retrain on the next request using the latest visitor data.", "ok")
    return redirect(url_for("admin.index"))
