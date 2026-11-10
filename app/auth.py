"""Authentication, sessions and CSRF protection."""
import functools
import hmac
import re
import secrets

from flask import (Blueprint, abort, flash, g, jsonify, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db

bp = Blueprint("auth", __name__)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD = 8


def csrf_token() -> str:
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    return session["_csrf"]


def init_security(app):
    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def _load_user_and_check_csrf():
        g.user = None
        uid = session.get("uid")
        if uid:
            g.user = get_db().execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
            if g.user is None:
                session.pop("uid", None)
        if app.config["CSRF_ENABLED"] and request.method in ("POST", "PUT", "PATCH", "DELETE"):
            sent = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token", "")
            expected = session.get("_csrf", "")
            if not expected or not hmac.compare_digest(sent, expected):
                abort(400, "Invalid or missing CSRF token")


def login_required(view):
    @functools.wraps(view)
    def wrapped(*a, **kw):
        if g.user is None:
            if request.path.startswith("/api/"):
                return jsonify(error="login required"), 401
            return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))
        return view(*a, **kw)
    return wrapped


def admin_required(view):
    @functools.wraps(view)
    @login_required
    def wrapped(*a, **kw):
        if g.user["role"] != "admin":
            abort(403)
        return view(*a, **kw)
    return wrapped


def _safe_next(target):
    return target if target and target.startswith("/") and not target.startswith("//") else url_for("views.home")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()[:60]
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        error = None
        if not name:
            error = "Please enter your name."
        elif not EMAIL_RE.match(email):
            error = "Please enter a valid email address."
        elif len(password) < MIN_PASSWORD:
            error = f"Password must be at least {MIN_PASSWORD} characters."
        db = get_db()
        if not error and db.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
            error = "An account with this email already exists."
        if error:
            flash(error, "error")
            return render_template("register.html", name=name, email=email), 400
        cur = db.execute("INSERT INTO users(name,email,password_hash) VALUES(?,?,?)",
                         (name, email, generate_password_hash(password)))
        db.commit()
        guest_prefs = session.get("prefs")
        session.clear()
        session["uid"] = cur.lastrowid
        if guest_prefs:  # keep preferences the visitor entered before signing up
            from .services import repo
            repo.save_user_prefs(db, cur.lastrowid, repo.clean_prefs(guest_prefs))
        flash("Welcome to TravelInsight! Tell us what you like to get recommendations.", "ok")
        return redirect(url_for("views.recommendations"))
    return render_template("register.html", name="", email="")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = get_db().execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], request.form.get("password", "")):
            session.clear()
            session["uid"] = user["id"]
            return redirect(_safe_next(request.args.get("next")))
        flash("Incorrect email or password.", "error")
        return render_template("login.html", email=email), 401
    return render_template("login.html", email="")


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("views.home"))
