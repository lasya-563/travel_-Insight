import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEV_SECRET = "dev-only-secret-change-me"


class Config:
    APP_ENV = os.environ.get("APP_ENV", "development")
    SECRET_KEY = os.environ.get("SECRET_KEY", DEV_SECRET)
    DATABASE_PATH = os.environ.get("DATABASE_PATH", str(BASE_DIR / "instance" / "travelinsight.db"))
    DESTINATIONS_CSV = os.environ.get("DESTINATIONS_CSV", str(BASE_DIR / "data" / "destinations.csv"))

    # 0 = choose K automatically with the silhouette score
    SEGMENT_K = int(os.environ.get("SEGMENT_K", "0"))
    # Number of synthetic demo visitors generated on first run (0 = none)
    DEMO_VISITORS = int(os.environ.get("DEMO_VISITORS", "450"))

    # First admin account (created on start-up when both are set; in development a
    # default is used so the demo works out of the box)
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024
    CSRF_ENABLED = True
    TESTING = False

    # Weight of the dataset's rating when blending with ratings given by users
    RATING_PRIOR_WEIGHT = 10

    @classmethod
    def validate(cls, cfg):
        if cfg.get("APP_ENV") == "production" and cfg.get("SECRET_KEY") == DEV_SECRET:
            raise RuntimeError("Set a strong SECRET_KEY environment variable in production.")
