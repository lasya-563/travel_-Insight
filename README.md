# TravelInsight – Smart Tourism Analytics & Visitor Intelligence System

Web application for the KPRIT IV B.Tech CSE major project (A.Y. 2026–27). It implements the features and
technologies described in the project PPT and documentation:

| Documentation item | Implementation |
|---|---|
| User login + preference selection | Flask sessions, hashed passwords (`app/auth.py`), live preference form (`/recommendations`) |
| Destination search & details | `/explore` (text search, category, state, budget, sort, pagination) and `/destination/<id>` |
| Content-based filtering + cosine similarity | `app/ml/recommender.py` – TF-IDF vectors (scikit-learn) + `cosine_similarity`; shows similarity score and the terms that matched |
| Visitor segmentation (K-Means) | `app/ml/segmentation.py` – StandardScaler → K chosen by silhouette → K-Means → auto-named clusters, PCA map |
| Tourism analytics dashboard | `/dashboard` – Plotly charts: categories, popularity, ratings, budget bands, trend, segments, heat-map |
| Destination data management | `/admin` – add / edit / delete, CSV import, retrain models |
| Python + Flask, Pandas, NumPy, Scikit-learn, Plotly, SQLite | exactly this stack |

**Real-time behaviour (for the review demo):** recommendations re-rank as you move any control; ratings, saves and
page views are written to the database and the dashboard (KPIs, charts, live-activity feed) refreshes every 10 s;
your own ratings/saves feed back into your recommendations; admin edits are picked up by all workers without a restart.

## Run locally (Python 3.10+)

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py run                                    # http://127.0.0.1:5000
```
The first start creates `instance/travelinsight.db` and seeds it. In development a demo admin is created:
**admin@travelinsight.local / admin12345** (never used in production – see below).
The dashboard loads Plotly from a CDN, so the machine needs internet access when presenting.

Tests: `pip install -r requirements-dev.txt && pytest -q`

## Deploy

All settings are environment variables (see `.env.example`). In production (`APP_ENV=production`) the app refuses to
start without a real `SECRET_KEY`, and creates the admin only if `ADMIN_EMAIL` and `ADMIN_PASSWORD` are set.

**Docker**
```bash
cp .env.example .env     # edit SECRET_KEY, ADMIN_EMAIL, ADMIN_PASSWORD
docker compose up --build        # http://localhost:8000   (data persists in a named volume)
```
**Render.com** – push to GitHub → New → Blueprint (uses `render.yaml`) → set `ADMIN_EMAIL` / `ADMIN_PASSWORD`.
Free instances have an ephemeral disk: the database is re-seeded on restart. Attach a persistent disk and set
`DATABASE_PATH` to keep users and ratings.
**Heroku / Railway / any VM** – `Procfile` runs `gunicorn wsgi:app`. Set `APP_ENV=production`, `SECRET_KEY`,
`COOKIE_SECURE=1` (when on HTTPS).

## Project layout
```
app/            Flask package (config, db, seed, auth, views, api, admin)
app/ml/         recommender.py, segmentation.py, store.py (self-refreshing model cache)
app/services/   repo.py (queries), analytics.py (dashboard numbers)
app/templates/  Jinja pages        app/static/  CSS + JS
data/destinations.csv   71 destinations (editable)
tests/          pytest suite       wsgi.py / manage.py   entry points
```

## How the scoring works
`match = 0.75 × (cosine ÷ best cosine) + 0.15 × rating + 0.10 × budget fit`. Destinations above 125 % of the budget
or below the minimum rating are excluded. Destination rating = blend of the dataset rating (weight 10) and ratings
given by users. Weights are constants at the top of `app/ml/recommender.py`.

## Important notes on data (please read before the review)
* `data/destinations.csv` is a **curated sample**; ratings and per-day budgets are indicative values for
  demonstration. Replace them with figures from your real dataset (Kaggle / tourism portals) and cite the source
  in your documentation – use the admin CSV import.
* On first run the app generates **450 synthetic visitor profiles and ~1,400 historical page views** so the
  segmentation and trend charts are not empty. These are fake and are labelled as demo data on the dashboard.
  Set `DEMO_VISITORS=0` to start empty (segmentation needs ≥ 20 visitor records; registered users who save
  preferences are added as visitors automatically).
* K-Means picks K automatically (silhouette score) – with the demo data it finds 4 segments. Segment names are
  generated from each cluster's dominant interests and budget.
* Out of scope, as in your PPT: booking, live weather/traffic, GPS tracking, chatbot. Database is SQLite; the
  documentation also mentions MySQL – moving to MySQL means swapping `app/db.py` and the SQL dialect specifics.
* Security basics included: password hashing, CSRF tokens, parameterised SQL, secure cookie flags, input validation.
  No rate-limiting or e-mail verification – add them before exposing to the public.
