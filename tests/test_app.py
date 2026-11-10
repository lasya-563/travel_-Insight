import io

import pytest

from app import create_app
from app.constants import CATEGORIES

PREFS = {"interests": ["Wildlife"], "activities": ["safari", "photography"], "budget": 5000, "min_rating": 4}


def test_pages_render(client):
    for url in ["/", "/explore", "/explore?q=tiger&category=Wildlife", "/recommendations", "/dashboard",
                "/login", "/register", "/destination/1", "/api/health"]:
        assert client.get(url).status_code == 200, url
    assert client.get("/destination/99999").status_code == 404
    assert client.get("/profile").status_code == 302


def test_recommendations_follow_interests_and_budget(client):
    r = client.post("/api/recommend", json=PREFS).get_json()
    assert r["results"], "expected matches"
    top = r["results"][:5]
    assert sum(x["category"] == "Wildlife" for x in top) >= 4
    assert all(x["budget_per_day"] <= 5000 * 1.25 and x["rating"] >= 4 for x in r["results"])
    assert r["results"] == sorted(r["results"], key=lambda x: -x["match"])
    assert r["segment"] and "·" in r["segment"]["label"]
    assert all(0 <= x["similarity"] <= 1 for x in r["results"])


def test_cold_start_and_bad_input(client):
    r = client.post("/api/recommend", json={}).get_json()
    assert r["cold_start"] and r["results"]
    r = client.post("/api/recommend", json={"interests": ["Nope"], "budget": "abc", "min_rating": "x"})
    assert r.status_code == 200
    assert client.post("/api/recommend", data="not json", content_type="text/plain").status_code == 200


def test_segmentation_is_sane(app):
    from app.db import connect
    with app.app_context():
        d = app.extensions["models"].segmenter(connect(app.config["DATABASE_PATH"])).describe()
    assert d["ready"] and 3 <= d["k"] <= 7 and d["silhouette"] > 0.1
    assert sum(c["size"] for c in d["clusters"]) == d["records"]
    assert len({c["label"] for c in d["clusters"]}) == d["k"]


def test_analytics_payload(client):
    d = client.get("/api/analytics").get_json()
    assert d["kpis"]["destinations"] >= 60
    assert {c["category"] for c in d["categories"]} == set(CATEGORIES)
    assert d["segmentation"]["ready"] and d["trend"] and d["top_destinations"]


def test_auth_flow_and_realtime_rating(user_client):
    assert user_client.get("/profile").status_code == 200
    before = user_client.get("/api/analytics").get_json()["kpis"]["user_ratings"]
    r = user_client.post("/api/destinations/1/rate", json={"rating": 5}).get_json()
    assert r["ok"] and r["user_ratings"] == 1
    after = user_client.get("/api/analytics").get_json()["kpis"]["user_ratings"]
    assert after == before + 1
    assert "rated 5★" in user_client.get("/api/analytics").get_json()["feed"][0]["text"]
    assert user_client.post("/api/destinations/1/rate", json={"rating": 9}).status_code == 400
    assert user_client.post("/api/destinations/1/save").get_json()["saved"] is True
    assert user_client.post("/api/preferences", json=PREFS).get_json()["ok"]
    assert user_client.post("/api/recommend", json=PREFS).get_json()["personalised_with_history"]


def test_auth_validation(client):
    assert client.post("/register", data={"name": "A", "email": "bad", "password": "password123"}).status_code == 400
    assert client.post("/register", data={"name": "A", "email": "a@b.co", "password": "short"}).status_code == 400
    assert client.post("/login", data={"email": "x@y.zz", "password": "nope"}).status_code == 401
    assert client.post("/api/destinations/1/rate", json={"rating": 3}).status_code == 401


def test_admin_protected_and_crud(client, user_client, admin_client):
    assert client.get("/admin/").status_code == 302
    assert user_client.get("/admin/").status_code == 403
    assert admin_client.get("/admin/").status_code == 200
    form = {"name": "Test Falls", "state": "Kerala", "category": "Nature", "activities": ["trekking"],
            "tags": "waterfall", "budget_per_day": "2000", "rating": "4.2", "best_season": "Jun-Sep",
            "description": "A test waterfall."}
    assert admin_client.post("/admin/destination/new", data=form).status_code == 302
    names = [x["name"] for x in client.get("/api/destinations?q=test falls").get_json()["results"]]
    assert names == ["Test Falls"]
    assert admin_client.post("/admin/destination/new", data=form).status_code == 400  # duplicate
    csv_data = b"name,state,category,activities,budget_per_day,rating\nCsv Town,Goa,Beach,water sports,3000,4.1\n"
    admin_client.post("/admin/import", data={"file": (io.BytesIO(csv_data), "d.csv")},
                      content_type="multipart/form-data")
    assert client.get("/api/destinations?q=csv town").get_json()["count"] == 1
    # new data is picked up by the recommender without a restart
    rec = client.post("/api/recommend", json={"keywords": "waterfall", "top_n": 3}).get_json()
    assert rec["results"][0]["name"] == "Test Falls"


def test_csrf_enforced(tmp_path):
    app = create_app({"DATABASE_PATH": str(tmp_path / "c.db"), "TESTING": True})
    c = app.test_client()
    assert c.post("/api/recommend", json={}).status_code == 400
    token = c.get("/login").get_data(as_text=True).split('name="csrf-token" content="')[1].split('"')[0]
    assert c.post("/api/recommend", json={}, headers={"X-CSRF-Token": token}).status_code == 200


def test_production_requires_secret(tmp_path):
    with pytest.raises(RuntimeError):
        create_app({"DATABASE_PATH": str(tmp_path / "p.db"), "APP_ENV": "production"})


def test_open_redirect_blocked(app, client):
    r = client.post("/login?next=//evil.com", data={"email": "admin@test.local", "password": "adminpass1"})
    assert r.status_code == 302 and "evil.com" not in r.headers["Location"]
