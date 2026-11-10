from flask import Flask, jsonify, render_template, request

from .config import Config
from .constants import ACTIVITIES, CATEGORIES, CATEGORY_COLORS, CATEGORY_ICONS, split_list
from .db import close_db, init_db
from .ml.store import ModelStore


def create_app(overrides: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)
    Config.validate(app.config)

    init_db(app)
    app.extensions["models"] = ModelStore(app.config["SEGMENT_K"])
    app.teardown_appcontext(close_db)

    from . import admin, api, auth, views
    auth.init_security(app)
    for bp in (auth.bp, views.bp, api.bp, admin.bp):
        app.register_blueprint(bp)

    @app.context_processor
    def inject_globals():
        return {"CATEGORIES": CATEGORIES, "ACTIVITIES": ACTIVITIES,
                "ICONS": CATEGORY_ICONS, "COLORS": CATEGORY_COLORS}

    app.jinja_env.filters["split"] = split_list

    @app.after_request
    def security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        if request.path.startswith("/api/"):
            resp.headers["Cache-Control"] = "no-store"
        return resp

    @app.errorhandler(404)
    def not_found(_e):
        if request.path.startswith("/api/"):
            return jsonify(error="not found"), 404
        return render_template("error.html", code=404, message="That page doesn't exist."), 404

    @app.errorhandler(400)
    def bad_request(e):
        if request.path.startswith("/api/"):
            return jsonify(error=getattr(e, "description", "bad request")), 400
        return render_template("error.html", code=400,
                               message="Bad request – please reload the page and try again."), 400

    @app.errorhandler(403)
    def forbidden(_e):
        if request.path.startswith("/api/"):
            return jsonify(error="forbidden"), 403
        return render_template("error.html", code=403, message="You don't have access to this page."), 403

    @app.errorhandler(413)
    def too_large(_e):
        return render_template("error.html", code=413, message="Uploaded file is too large (max 2 MB)."), 413

    @app.errorhandler(500)
    def server_error(_e):
        if request.path.startswith("/api/"):
            return jsonify(error="server error"), 500
        return render_template("error.html", code=500, message="Something went wrong on our side."), 500

    return app
