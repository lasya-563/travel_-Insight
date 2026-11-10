"""Small CLI:  python manage.py run | init-db | create-admin EMAIL PASSWORD | retrain"""
import sys

from app import create_app
from app.db import bump_meta, connect


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "run"
    app = create_app()  # creates tables + seeds on first run
    if cmd == "run":
        import os
        app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", 5000)),
                debug=app.config["APP_ENV"] != "production")
    elif cmd == "init-db":
        print("Database ready at", app.config["DATABASE_PATH"])
    elif cmd == "create-admin" and len(argv) == 4:
        from werkzeug.security import generate_password_hash
        conn = connect(app.config["DATABASE_PATH"])
        conn.execute(
            "INSERT INTO users(name,email,password_hash,role) VALUES('Administrator',?,?,'admin') "
            "ON CONFLICT(email) DO UPDATE SET password_hash=excluded.password_hash, role='admin'",
            (argv[2].strip().lower(), generate_password_hash(argv[3])))
        conn.commit()
        print("Admin account ready:", argv[2])
    elif cmd == "retrain":
        conn = connect(app.config["DATABASE_PATH"])
        bump_meta(conn, "seg_version"); bump_meta(conn, "rec_version"); conn.commit()
        print("Models will retrain on next request.")
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv)
