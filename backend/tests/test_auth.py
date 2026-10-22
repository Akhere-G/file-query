from tests.conftest import PASSWORD


def test_register_login_me(client):
    res = client.post(
        "/api/auth/register",
        json={"username": "Ann", "email": "ann@example.com", "password": PASSWORD},
    )
    assert res.status_code == 201

    res = client.post(
        "/api/auth/login", json={"email": "ann@example.com", "password": PASSWORD}
    )
    assert res.status_code == 200
    headers = {"Authorization": f"Bearer {res.json()['access_token']}"}
    assert client.get("/api/auth/me", headers=headers).json()["email"] == "ann@example.com"


def test_wrong_password_rejected(client, make_user):
    make_user("bob@example.com")
    res = client.post(
        "/api/auth/login", json={"email": "bob@example.com", "password": "Wrong1234"}
    )
    assert res.status_code == 401


def test_me_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401


def test_duplicate_email_conflicts(client, make_user):
    make_user("dup@example.com")
    res = client.post(
        "/api/auth/register",
        json={"username": "X", "email": "dup@example.com", "password": PASSWORD},
    )
    assert res.status_code == 409
