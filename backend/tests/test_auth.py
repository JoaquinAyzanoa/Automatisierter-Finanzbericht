import pytest

from app.core.security import hash_password
from app.models.user import User


@pytest.fixture
def seeded_user(client):
    """Insert a known user directly via the overridden session."""
    from app.api.deps import get_db

    gen = client.app.dependency_overrides[get_db]()
    db = next(gen)
    user = User(
        username="tester",
        hashed_password=hash_password("s3cret"),
        is_admin=True,
    )
    db.add(user)
    db.commit()
    yield user
    try:
        next(gen)
    except StopIteration:
        pass


def test_login_success_and_me(client, seeded_user):
    resp = client.post(
        "/api/v1/auth/login", json={"username": "tester", "password": "s3cret"}
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    assert token

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["username"] == "tester"
    assert me.json()["is_admin"] is True


def test_login_wrong_password(client, seeded_user):
    resp = client.post(
        "/api/v1/auth/login", json={"username": "tester", "password": "wrong"}
    )
    assert resp.status_code == 401


def test_me_requires_auth(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401
