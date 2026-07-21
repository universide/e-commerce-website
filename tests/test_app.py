import re

import pytest

from app import create_app, db, seed_data


@pytest.fixture()
def app(tmp_path):
    database_path = tmp_path / "test.db"
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}",
        }
    )
    with app.app_context():
        db.create_all()
        seed_data()
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def csrf_token(client, path="/"):
    response = client.get(path)
    match = re.search(r'name="_csrf_token" value="([^"]+)"', response.get_data(as_text=True))
    assert match is not None
    return match.group(1)


def test_catalogue_lists_seeded_products(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Wireless Mouse" in response.data
    assert b"Noise Cancelling Headphones" in response.data


def test_registration_creates_authenticated_profile(client):
    token = csrf_token(client, "/register")
    response = client.post(
        "/register",
        data={"_csrf_token": token, "username": "portfolio-user", "password": "Strong!123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"portfolio-user" in response.data


def test_cart_and_checkout_flow(client):
    token = csrf_token(client)
    response = client.post(
        "/cart/items/1",
        data={"_csrf_token": token},
        follow_redirects=True,
    )
    assert b"Wireless Mouse" in response.data
    assert b"$29.99" in response.data

    response = client.post(
        "/checkout",
        data={"_csrf_token": token},
        follow_redirects=True,
    )
    assert b"simulated checkout" in response.data
    assert b"$29.99" in response.data
    assert b"Your cart is empty" in client.get("/cart").data


def test_state_changes_require_post_and_valid_csrf(client):
    assert client.get("/cart/items/1").status_code == 405
    assert client.post("/cart/items/1", data={}).status_code == 400
