from datetime import datetime, timedelta, timezone, UTC

import jwt
import pytest

from src.settings import settings


def token(sub="user@example.com", *, key=None, algorithm="HS256", expires=timedelta(minutes=5), **extra):
    claims = {**extra}
    if sub is not None:
        claims["sub"] = sub
    if expires is not None:
        claims["exp"] = datetime.now(UTC) + expires
    return jwt.encode(claims, key if key is not None else settings.SECRET_KEY, algorithm=algorithm)


@pytest.fixture
def registered(make_user):
    me, headers = make_user("user@example.com")
    return me, headers["Authorization"].split()[1]


def me(client, bearer):
    return client.get("/api/auth/me", headers={"Authorization": f"Bearer {bearer}"})


def test_a_genuine_token_is_accepted(client, registered):
    assert me(client, registered[1]).status_code == 200


@pytest.mark.parametrize(
    "bad_token",
    [
        pytest.param(lambda: token(expires=timedelta(minutes=-1)), id="expired"),
        pytest.param(
            lambda: token(expires=None),
            id="no-expiry",
            marks=pytest.mark.xfail(
                strict=True,
                reason="Known gap: jwt.decode does not require the exp claim, so a correctly "
                "signed token without an expiry never expires",
            ),
        ),
        pytest.param(lambda: token(key="another-secret-another-secret-another-secret"), id="wrong-signature"),
        pytest.param(lambda: token(key=settings.SECRET_KEY * 2, algorithm="HS512"), id="wrong-algorithm"),
        pytest.param(lambda: token(sub=None), id="no-subject"),
        pytest.param(lambda: token(sub="ghost@example.com"), id="user-does-not-exist"),
        pytest.param(lambda: jwt.encode({"sub": "user@example.com"}, key="", algorithm="none"), id="alg-none"),
        pytest.param(lambda: "not.a.jwt", id="garbage"),
        pytest.param(lambda: "", id="empty"),
    ],
)
def test_invalid_tokens_are_rejected(client, registered, bad_token):
    bearer = bad_token()
    res = me(client, bearer) if bearer else client.get("/api/auth/me", headers={"Authorization": "Bearer "})
    assert res.status_code == 401


def test_a_tampered_payload_is_rejected(client, registered):
    header, _, signature = registered[1].split(".")
    forged_payload = token(sub="admin@example.com").split(".")[1]

    assert me(client, f"{header}.{forged_payload}.{signature}").status_code == 401


def test_a_token_stays_valid_only_for_its_own_user(client, make_user):
    make_user("a@example.com")
    _, headers_b = make_user("b@example.com")

    body = client.get("/api/auth/me", headers=headers_b).json()

    assert body["email"] == "b@example.com"


@pytest.mark.parametrize("path", ["/api/projects", "/api/auth/me"])
def test_protected_routes_need_a_bearer_token(client, path):
    assert client.get(path).status_code == 401
    assert client.get(path, headers={"Authorization": "Basic abc"}).status_code == 401


def test_responses_never_contain_the_password_hash(client, registered):
    body = me(client, registered[1]).json()

    assert "password" not in str(body).lower()
    assert "hash" not in str(body).lower()


def test_the_demo_login_is_unavailable_until_a_demo_user_exists(client):
    assert client.post("/api/auth/demo").status_code == 503


def test_demo_accounts_cannot_sign_in_with_a_password(client, db):
    from src.features.auth.user_model import User
    from src.features.auth.user_service import get_password_hash

    db.add(User(username="Demo", email="demo@example.com", password_hash=get_password_hash("Passw0rdTest"), is_demo=True))
    db.commit()

    res = client.post("/api/auth/login", json={"email": "demo@example.com", "password": "Passw0rdTest"})

    assert res.status_code == 401
