"""First-run seeding: destinations from CSV, synthetic DEMO visitors/activity, admin account.

The destination CSV is a curated sample (ratings and budgets are indicative values meant
for demonstration). Visitors and the page-view history are *synthetic* and exist only so
the segmentation and analytics screens have something to show on a fresh install.
Replace them with real records before drawing any conclusions.
"""
import csv
import random
from datetime import datetime, timedelta, timezone

import numpy as np
from werkzeug.security import generate_password_hash

from .constants import CATEGORIES, CATEGORY_COLS, split_list

DEV_ADMIN = ("admin@travelinsight.local", "admin12345")

# name, mean interest scores (0-5) per category, budget mean, trip-days mean
PERSONAS = [
    ("adventure", {"Adventure": 4.5, "Hill Station": 3.6, "Nature": 3.0, "Wildlife": 1.8}, 3600, 7),
    ("heritage", {"Heritage": 4.6, "Spiritual": 3.0, "City": 3.0}, 3000, 5),
    ("beach", {"Beach": 4.6, "City": 2.6, "Nature": 2.0}, 4600, 5),
    ("wildlife", {"Wildlife": 4.6, "Nature": 4.0, "Adventure": 2.0}, 4300, 6),
    ("pilgrim", {"Spiritual": 4.7, "Heritage": 3.2}, 1800, 4),
    ("urban", {"City": 4.4, "Beach": 2.4, "Heritage": 2.2}, 6800, 3),
]
FIRST = ["Aarav", "Diya", "Rohan", "Ananya", "Vikram", "Meera", "Arjun", "Isha", "Karthik", "Sneha",
         "Rahul", "Priya", "Nikhil", "Divya", "Sanjay", "Pooja", "Manoj", "Lakshmi", "Tarun", "Neha"]


def _set_meta(conn, key, value):
    conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", (key, str(value)))


def seed_destinations(conn, csv_path):
    if conn.execute("SELECT COUNT(*) FROM destinations").fetchone()[0]:
        return
    with open(csv_path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            conn.execute(
                "INSERT INTO destinations(name,state,category,activities,tags,budget_per_day,"
                "base_rating,best_season,description) VALUES(?,?,?,?,?,?,?,?,?)",
                (r["name"].strip(), r["state"].strip(), r["category"].strip(), r["activities"].strip(),
                 r["tags"].strip(), int(r["budget_per_day"]), float(r["rating"]),
                 r["best_season"].strip(), r["description"].strip()),
            )


def seed_visitors_and_activity(conn, n_visitors):
    if n_visitors <= 0 or conn.execute("SELECT COUNT(*) FROM visitors").fetchone()[0]:
        return
    rng = np.random.default_rng(42)
    py_rng = random.Random(42)
    cols = list(CATEGORY_COLS.values())
    weights = np.array([0.2, 0.2, 0.15, 0.15, 0.1, 0.2])
    weights = weights / weights.sum()

    dests = conn.execute("SELECT id, category, base_rating FROM destinations").fetchall()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for i in range(n_visitors):
        p = PERSONAS[rng.choice(len(PERSONAS), p=weights)]
        scores = {c: float(np.clip(rng.normal(p[1].get(c, 0.9), 0.7), 0, 5)) for c in CATEGORIES}
        budget = float(np.clip(rng.normal(p[2], p[2] * 0.2), 800, 12000))
        days = float(np.clip(round(rng.normal(p[3], 1.2)), 2, 14))
        conn.execute(
            f"INSERT INTO visitors(name,source,budget_per_day,trip_days,{','.join(cols)}) "
            f"VALUES(?,?,?,?,{','.join('?' * len(cols))})",
            (f"{py_rng.choice(FIRST)} #{i + 1}", "demo", round(budget), days,
             *[round(scores[c], 2) for c in CATEGORIES]),
        )
        # a few synthetic page views in line with the visitor's interests, spread over 30 days
        w = np.array([max(scores[d["category"]], 0.05) * d["base_rating"] for d in dests])
        picks = rng.choice(len(dests), size=int(rng.integers(2, 6)), p=w / w.sum())
        for idx in picks:
            ts = now - timedelta(days=int(rng.integers(0, 30)), minutes=int(rng.integers(0, 1440)))
            conn.execute(
                "INSERT INTO interactions(user_id,destination_id,type,created_at) VALUES(NULL,?, 'view', ?)",
                (dests[idx]["id"], ts.strftime("%Y-%m-%d %H:%M:%S")),
            )


def ensure_admin(conn, cfg):
    email, password = cfg.get("ADMIN_EMAIL"), cfg.get("ADMIN_PASSWORD")
    if not (email and password):
        if cfg.get("APP_ENV") == "production":
            return
        email, password = DEV_ADMIN
    email = email.strip().lower()
    if conn.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
        return
    conn.execute(
        "INSERT INTO users(name,email,password_hash,role) VALUES('Administrator',?,?,'admin')",
        (email, generate_password_hash(password)),
    )


def seed_all(conn, cfg):
    seed_destinations(conn, cfg["DESTINATIONS_CSV"])
    seed_visitors_and_activity(conn, cfg["DEMO_VISITORS"])
    ensure_admin(conn, cfg)
    for key in ("rec_version", "seg_version"):
        conn.execute("INSERT OR IGNORE INTO meta(key,value) VALUES(?, '1')", (key,))
