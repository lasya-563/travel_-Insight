"""Descriptive tourism analytics (documentation section 4.6) returned as JSON-ready dicts."""
from ..constants import BUDGET_BANDS, CATEGORIES, CATEGORY_COLORS
from . import repo


def _verb(kind, value):
    return {"view": "viewed", "save": "saved", "rating": f"rated {value}★" if value else "rated"}[kind]


def build(db, segmenter) -> dict:
    df = repo.destinations_df(db)
    n_dest = len(df)
    kpis = {
        "destinations": n_dest,
        "visitors": db.execute("SELECT COUNT(*) FROM visitors").fetchone()[0],
        "registered_users": db.execute("SELECT COUNT(*) FROM users WHERE role='tourist'").fetchone()[0],
        "user_ratings": db.execute("SELECT COUNT(*) FROM ratings").fetchone()[0],
        "avg_rating": round(float(df["rating"].mean()), 2) if n_dest else 0,
        "events_24h": db.execute(
            "SELECT COUNT(*) FROM interactions WHERE created_at >= datetime('now','-1 day')").fetchone()[0],
    }

    cat = df.groupby("category").agg(count=("id", "count"), avg_rating=("rating", "mean"),
                                     avg_budget=("budget_per_day", "mean"),
                                     popularity=("popularity", "sum")).reset_index()
    cat_rows = [{"category": c, "count": int(r["count"]), "avg_rating": round(float(r["avg_rating"]), 2),
                 "avg_budget": int(r["avg_budget"]), "popularity": int(r["popularity"]),
                 "color": CATEGORY_COLORS[c]}
                for c in CATEGORIES for _, r in cat[cat["category"] == c].iterrows()]

    top = df.sort_values(["popularity", "rating"], ascending=False).head(10)
    top_rows = [{"id": int(r["id"]), "name": r["name"], "category": r["category"],
                 "popularity": int(r["popularity"]), "rating": float(r["rating"])}
                for _, r in top.iterrows()]
    best = df.sort_values(["rating", "user_ratings"], ascending=False).head(8)
    best_rows = [{"id": int(r["id"]), "name": r["name"], "rating": float(r["rating"])}
                 for _, r in best.iterrows()]

    bands = [{"band": name, "count": int(((df["budget_per_day"] >= lo) & (df["budget_per_day"] < hi)).sum())}
             for name, lo, hi in BUDGET_BANDS]
    states = (df.groupby("state")["id"].count().sort_values(ascending=False).head(10))
    state_rows = [{"state": s, "count": int(c)} for s, c in states.items()]

    trend = [dict(date=r["d"], views=r["v"], ratings=r["r"], saves=r["s"]) for r in db.execute(
        "SELECT date(created_at) d, SUM(type='view') v, SUM(type='rating') r, SUM(type='save') s "
        "FROM interactions WHERE created_at >= date('now','-13 day') GROUP BY d ORDER BY d")]

    feed = []
    for r in db.execute(
            "SELECT i.type, i.value, i.created_at, d.name dest, u.name uname FROM interactions i "
            "JOIN destinations d ON d.id=i.destination_id LEFT JOIN users u ON u.id=i.user_id "
            "ORDER BY i.id DESC LIMIT 8"):
        who = r["uname"].split()[0] if r["uname"] else "A visitor"
        feed.append({"text": f"{who} {_verb(r['type'], r['value'])} {r['dest']}", "at": r["created_at"]})

    return {
        "kpis": kpis, "categories": cat_rows, "top_destinations": top_rows, "best_rated": best_rows,
        "budget_bands": bands, "states": state_rows, "trend": trend, "feed": feed,
        "segmentation": segmenter.describe() if segmenter else {"ready": False},
        "category_colors": CATEGORY_COLORS,
        "data_note": "Visitor records and earlier page views in a fresh install are synthetic demo data.",
    }
