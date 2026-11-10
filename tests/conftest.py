import pytest

from app import create_app


@pytest.fixture()
def app(tmp_path):
    return create_app({
        "DATABASE_PATH": str(tmp_path / "test.db"), "TESTING": True, "CSRF_ENABLED": False,
        "ADMIN_EMAIL": "admin@test.local", "ADMIN_PASSWORD": "adminpass1",
    })


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def user_client(app):
    c = app.test_client()
    c.post("/register", data={"name": "Test User", "email": "t@example.com", "password": "password123"})
    return c


@pytest.fixture()
def admin_client(app):
    c = app.test_client()
    c.post("/login", data={"email": "admin@test.local", "password": "adminpass1"})
    return c
