# TravelInsight — Smart Tourism Analytics & Visitor Intelligence System

A working prototype for a final-year project: a Flask website that predicts
attraction footfall, classifies visitor review sentiment, and recommends
attractions based on interests — with a live analytics dashboard.

## Quick start

```bash
cd travelinsight
pip install -r requirements.txt

# (datasets and the trained model are already included, but to regenerate them:)
python3 data/generate_data.py
python3 models/train_footfall_model.py

python3 app.py
```

Open **http://127.0.0.1:5000** in your browser.

## What's inside

| Layer | Technology | Where |
|---|---|---|
| Frontend | HTML, CSS, vanilla JS, Chart.js | `templates/`, `static/` |
| Backend / API | Flask (Python) | `app.py` |
| ML — footfall forecasting | scikit-learn `RandomForestRegressor` | `models/train_footfall_model.py` |
| NLP — review sentiment | Lexicon-based scorer (swappable for a transformer model) | `utils/sentiment.py` |
| Recommendation engine | TF-IDF + cosine similarity (content-based filtering) | `utils/recommend.py` |
| Data | Synthetic datasets modeling 2 years of daily footfall + reviews for 12 Hyderabad attractions | `data/` |

## Features implemented

1. **Analytics dashboard** — visitor trend line, sentiment doughnut chart,
   top-attractions bar chart, weather-vs-turnout chart, live KPI counters.
2. **Footfall prediction** — pick an attraction, date and expected weather;
   a trained ML model forecasts expected visitor count (R² ≈ 0.96 on the
   synthetic dataset's held-out test split).
3. **Recommendation engine** — pick interest tags (history, nature, sunset,
   etc.); results blend content similarity with average review sentiment
   per attraction.
4. **Sentiment-on-demand** — type or paste a review; it's classified
   instantly and folded live into the dashboard's sentiment chart.

## Why this data is synthetic

Real visitor-count data for specific attractions is not publicly available
at daily granularity, and scraping review platforms raises ToS/consent
issues that aren't appropriate to build a coursework prototype on. The
generator (`data/generate_data.py`) encodes realistic patterns — weekend
and holiday spikes, seasonal swings, weather sensitivity — documented in
your literature survey as an explicit assumption/limitation. For a real
deployment, replace `data/footfall_history.csv` with actual ticketing/
footfall-counter exports and `data/reviews.csv` with reviews collected
through a proper API/consented pipeline, then re-run the two scripts above.

## Extending this into the "unique factor" of your project

The individual pieces here (footfall prediction, sentiment analysis,
recommendations) all exist separately in prior work. What's still a fair,
defensible novelty claim for a final-year project is **combining them into
one closed loop**: predicted footfall + live sentiment adjust what gets
recommended and to whom, and — if you add it — feed a **crowd-alert layer**
(e.g. flag attractions predicted to be over a comfortable-capacity
threshold on a given day and nudge visitors toward similar, less-crowded
alternatives). That loop, not any single model, is what your literature
survey should point to as the gap in existing systems.

Natural next additions if you have time before submission:
- Swap the lexicon sentiment scorer for a fine-tuned transformer
  (e.g. DistilBERT via Hugging Face `transformers`) — the interface in
  `utils/sentiment.py` is designed so this is a drop-in change.
- Add a simple map view (Leaflet.js) plotting attractions and predicted
  crowd levels.
- Add a login + favorites list so recommendations personalize over time.
- Swap synthetic data for a real open dataset (state tourism department
  open data portals, or Google Places popularity data where licensing
  permits) once you're past the prototype stage.
