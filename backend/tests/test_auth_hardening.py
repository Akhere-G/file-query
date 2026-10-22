import pytest

from src.features.auth import user_routes, user_service
from tests.conftest import PASSWORD


def register(client, email, password=PASSWORD):
    return client.post(
        "/api/auth/register",
        json={"username": "T", "email": email, "password": password},
    )


def test_email_is_case_insensitive(client):
    assert register(client, "Mixed.Case@Example.com").status_code == 201
    for variant in ("mixed.case@example.com", "MIXED.CASE@EXAMPLE.COM"):
        res = client.post("/api/auth/login", json={"email": variant, "password": PASSWORD})
        assert res.status_code == 200, variant
    assert register(client, "MIXED.case@example.com").status_code == 409


def test_form_login_is_case_insensitive(client):
    register(client, "form@example.com")
    res = client.post("/api/auth/token", data={"username": "FORM@example.com", "password": PASSWORD})
    assert res.status_code == 200


def test_concurrent_duplicate_registration_is_a_conflict(client, monkeypatch):
    register(client, "race@example.com")
    monkeypatch.setattr(user_routes.user_service, "get_user_by_email", lambda *a, **k: None)
    assert register(client, "race@example.com").status_code == 409


def test_unknown_email_still_checks_a_password_hash(client, monkeypatch):
    hashes = []
    check = user_service.check_password_hash

    def counting(password, hashed):
        hashes.append(hashed)
        return check(password, hashed)

    monkeypatch.setattr(user_service, "check_password_hash", counting)
    res = client.post("/api/auth/login", json={"email": "ghost@example.com", "password": PASSWORD})
    assert res.status_code == 401
    assert len(hashes) == 1


@pytest.mark.parametrize("length, status", [(100, 201), (128, 201), (129, 422)])
def test_password_length_limit(client, length, status):
    password = "Aa1" + "x" * (length - 3)
    assert register(client, f"len{length}@example.com", password).status_code == status


def test_file_responses_do_not_include_storage_keys(client, make_user):
    _, headers = make_user()
    res = client.post(
        "/api/files",
        json=[{"name": "a.txt", "mimeType": "text/plain", "size": 5}],
        headers=headers,
    )
    files = client.get(f"/api/projects/{res.json()['projectId']}/files", headers=headers).json()
    assert "storageKey" not in files[0]
