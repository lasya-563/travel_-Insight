"""
TravelInsight: Smart Tourism Analytics & Visitor Intelligence System
---------------------------------------------------------------------
A single-service Flask app that serves:
  - A dashboard UI (templates/index.html) with charts
  - REST API endpoints used by the frontend JS:
      GET  /api/spots              -> list of attractions
      GET  /api/stats              -> aggregated analytics for the dashboard
      POST /api/predict            -> ML footfall prediction for a spot/date
      POST /api/recommend          -> content-based attraction recommendations
      POST /api/sentiment          -> analyze a new review's sentiment

Run:
    pip install -r requirements.txt
    python3 app.py
Then open http://127.0.0.1:5000
"""
import os
import pickle
import datetime
from collections import defaultdict

import pandas as pd
from flask import Flask, render_template, request, jsonify

from utils.sentiment import analyze, batch_analyze
from utils.recommend import recommend

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MODEL_FILE = os.path.join(BASE_DIR, "models", "footfall_model.pkl")

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Load data + model once at startup
# ---------------------------------------------------------------------------
spots_df = pd.read_csv(os.path.join(DATA_DIR, "tourist_spots.csv"))
footfall_df = pd.read_csv(os.path.join(DATA_DIR, "footfall_history.csv"))
reviews_df = pd.read_csv(os.path.join(DATA_DIR, "reviews.csv"))

with open(MODEL_FILE, "rb") as f:
    MODEL_BUNDLE = pickle.load(f)

# In-memory store for reviews submitted during this server session
# (kept separate from the CSV so the demo dataset file stays untouched)
SESSION_REVIEWS = []


def _season_for_month(month: int) -> str:
    if month in (12, 1, 2):
        return "Winter"
    if month in (3, 4, 5, 6):
        return "Summer"
    if month in (7, 8, 9):
        return "Monsoon"
    return "Autumn"


def _spot_sentiment_scores():
    """Average sentiment score per spot_id from the review dataset, used to
    nudge the recommendation engine towards well-reviewed attractions."""
    scores = defaultdict(list)
    for _, row in reviews_df.iterrows():
        result = analyze(row["review_text"])
        scores[str(row["spot_id"])].append(result["score"])
    return {sid: (sum(v) / len(v)) for sid, v in scores.items()}


SPOT_SENTIMENT_SCORES = _spot_sentiment_scores()


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html", spots=spots_df.to_dict(orient="records"))


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------
@app.route("/api/spots")
def api_spots():
    return jsonify(spots_df.to_dict(orient="records"))


@app.route("/api/stats")
def api_stats():
    # 1) Visitor trend for the last 30 available days, summed across all spots
    df = footfall_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    last_date = df["date"].max()
    window = df[df["date"] > last_date - pd.Timedelta(days=30)]
    trend = window.groupby("date")["visitors"].sum().reset_index()
    trend_labels = trend["date"].dt.strftime("%d %b").tolist()
    trend_values = trend["visitors"].tolist()

    # 2) Total visitors per attraction (all-time) -> top attractions
    totals = (
        df.groupby("spot_name")["visitors"].sum().sort_values(ascending=False)
    )
    top_labels = totals.head(8).index.tolist()
    top_values = totals.head(8).values.tolist()

    # 3) Sentiment distribution across all reviews (dataset + session)
    all_texts = reviews_df["review_text"].tolist() + [r["text"] for r in SESSION_REVIEWS]
    results = batch_analyze(all_texts)
    dist = defaultdict(int)
    for r in results:
        dist[r["label"]] += 1

    # 4) Weather impact (avg visitors by weather condition)
    weather_avg = df.groupby("weather")["visitors"].mean().round(0)

    return jsonify({
        "trend_labels": trend_labels,
        "trend_values": trend_values,
        "top_labels": top_labels,
        "top_values": top_values,
        "sentiment_distribution": dict(dist),
        "weather_impact": weather_avg.to_dict(),
        "total_reviews": len(all_texts),
        "avg_rating": round(float(reviews_df["rating"].mean()), 2),
    })


@app.route("/api/predict", methods=["POST"])
def api_predict():
    payload = request.get_json(force=True)
    spot_id = int(payload["spot_id"])
    date_str = payload["date"]
    weather = payload.get("weather", "Sunny")

    date = datetime.date.fromisoformat(date_str)
    weekday = date.weekday()
    is_weekend = 1 if weekday >= 5 else 0
    season = _season_for_month(date.month)

    season_map = MODEL_BUNDLE["season_map"]
    weather_map = MODEL_BUNDLE["weather_map"]
    model = MODEL_BUNDLE["model"]

    season_enc = season_map.get(season, 0)
    weather_enc = weather_map.get(weather, 0)

    # Simple heuristic for known public holidays (extend as needed)
    holiday_days = {"01-01", "01-26", "08-15", "10-02", "12-25"}
    is_holiday = 1 if date.strftime("%m-%d") in holiday_days else 0

    feature_cols = MODEL_BUNDLE["feature_cols"]
    features = pd.DataFrame(
        [[spot_id, weekday, is_weekend, is_holiday, season_enc, weather_enc]],
        columns=feature_cols,
    )
    prediction = model.predict(features)[0]

    spot_row = spots_df[spots_df["id"] == spot_id].iloc[0]

    return jsonify({
        "spot_name": spot_row["name"],
        "date": date_str,
        "weekday": date.strftime("%A"),
        "season": season,
        "weather": weather,
        "is_holiday": bool(is_holiday),
        "predicted_visitors": int(round(prediction)),
    })


@app.route("/api/recommend", methods=["POST"])
def api_recommend():
    payload = request.get_json(force=True)
    interests = payload.get("interests", [])
    if isinstance(interests, str):
        interests = [i.strip() for i in interests.split(",") if i.strip()]

    results = recommend(interests, top_n=5, sentiment_scores=SPOT_SENTIMENT_SCORES)
    return jsonify(results)


@app.route("/api/sentiment", methods=["POST"])
def api_sentiment():
    payload = request.get_json(force=True)
    text = payload.get("text", "")
    result = analyze(text)
    SESSION_REVIEWS.append({"text": text, "label": result["label"]})
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
