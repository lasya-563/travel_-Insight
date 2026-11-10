"""SQLite access layer (stdlib sqlite3, no ORM needed for this scale)."""
import os
import sqlite3

from flask import current_app, g

from .constants import CATEGORY_COLS

_VISITOR_COLS = ",\n ".join(f"{col} REAL NOT NULL DEFAULT 0" for col in CATEGORY_COLS.values())

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT NOT NULL,
 email TEXT NOT NULL UNIQUE,
 password_hash TEXT NOT NULL,
 role TEXT NOT NULL DEFAULT 'tourist' CHECK (role IN ('tourist','admin')),
 interests TEXT NOT NULL DEFAULT '',
 activities TEXT NOT NULL DEFAULT '',
 keywords TEXT NOT NULL DEFAULT '',
 budget INTEGER,
 min_rating REAL NOT NULL DEFAULT 0,
 trip_days INTEGER NOT NULL DEFAULT 5,
 created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS destinations (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT NOT NULL UNIQUE COLLATE NOCASE,
 state TEXT NOT NULL,
 category TEXT NOT NULL,
 activities TEXT NOT NULL,
 tags TEXT NOT NULL DEFAULT '',
 budget_per_day INTEGER NOT NULL,
 base_rating REAL NOT NULL,
 best_season TEXT NOT NULL DEFAULT '',
 description TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS ratings (
 user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 destination_id INTEGER NOT NULL REFERENCES destinations(id) ON DELETE CASCADE,
 rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
 created_at TEXT NOT NULL DEFAULT (datetime('now')),
 PRIMARY KEY (user_id, destination_id)
);
CREATE TABLE IF NOT EXISTS saved (
 user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 destination_id INTEGER NOT NULL REFERENCES destinations(id) ON DELETE CASCADE,
 created_at TEXT NOT NULL DEFAULT (datetime('now')),
 PRIMARY KEY (user_id, destination_id)
);
CREATE TABLE IF NOT EXISTS interactions (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
 destination_id INTEGER NOT NULL REFERENCES destinations(id) ON DELETE CASCADE,
 type TEXT NOT NULL CHECK (type IN ('view','rating','save')),
 value INTEGER,
 created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_interactions_created ON interactions(created_at);
CREATE INDEX IF NOT EXISTS idx_interactions_dest ON interactions(destination_id);
CREATE TABLE IF NOT EXISTS visitors (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT NOT NULL,
 source TEXT NOT NULL DEFAULT 'demo' CHECK (source IN ('demo','user')),
 user_id INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,
 budget_per_day REAL NOT NULL,
 trip_days REAL NOT NULL,
 {_VISITOR_COLS},
 created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


def connect(path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE_PATH"])
    return g.db


def close_db(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def get_meta(db, key: str, default: str = "0") -> str:
    row = db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def bump_meta(db, key: str):
    db.execute(
        "INSERT INTO meta(key,value) VALUES(?, '1') "
        "ON CONFLICT(key) DO UPDATE SET value = CAST(value AS INTEGER) + 1",
        (key,),
    )


def init_db(app):
    """Create tables and seed data. Idempotent and safe when several workers start together."""
    from . import seed

    conn = connect(app.config["DATABASE_PATH"])
    try:
        conn.executescript(SCHEMA)
        conn.execute("BEGIN IMMEDIATE")  # serialises concurrent first-run seeding
        seed.seed_all(conn, app.config)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
