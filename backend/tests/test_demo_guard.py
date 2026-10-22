import pytest

from src.features.auth.user_model import User
from src.features.auth.user_service import get_password_hash
from src.features.chat.message_model import Message
from src.settings import settings
from tests.helpers import add_project_with_chunk


@pytest.fixture
def demo(client, db):
    user = User(
        username="Demo User",
        email="demo@example.com",
        password_hash=get_password_hash("Unused1234"),
        is_demo=True,
    )
    db.add(user)
    db.commit()
    project_id = add_project_with_chunk(db, user.id)
    res = client.post("/api/auth/demo")
    assert res.status_code == 200
    return project_id, {"Authorization": f"Bearer {res.json()['access_token']}"}


def ask(client, project_id, headers):
    return client.post(
        f"/api/projects/{project_id}/messages", json={"content": "banana"}, headers=headers
    )


def test_demo_can_read(client, demo):
    project_id, headers = demo
    assert client.get("/api/projects", headers=headers).status_code == 200
    assert client.get(f"/api/projects/{project_id}/files", headers=headers).status_code == 200
    assert client.get(f"/api/projects/{project_id}/messages", headers=headers).status_code == 200


def test_demo_cannot_change_anything(client, demo):
    project_id, headers = demo
    file_id = client.get(f"/api/projects/{project_id}/files", headers=headers).json()[0]["id"]
    body = [{"name": "a.txt", "mimeType": "text/plain", "size": 5}]

    responses = [
        client.post("/api/files", json=body, headers=headers),
        client.post("/api/files/confirm", json=[{"id": file_id}], headers=headers),
        client.delete(f"/api/files/{file_id}", headers=headers),
        client.patch(f"/api/projects/{project_id}", json={"name": "x"}, headers=headers),
        client.delete(f"/api/projects/{project_id}", headers=headers),
    ]

    assert [r.status_code for r in responses] == [403] * 5
    assert "read-only" in responses[0].json()["detail"]
    assert client.get(f"/api/projects/{project_id}", headers=headers).status_code == 200


def test_demo_chat_answers_without_saving(client, db, demo):
    project_id, headers = demo
    res = ask(client, project_id, headers)
    assert res.status_code == 200, res.text
    assert res.json()["id"] < 0
    assert res.json()["citations"]
    assert db.query(Message).count() == 0


def test_demo_daily_chat_cap(client, demo, monkeypatch):
    project_id, headers = demo
    monkeypatch.setattr(settings, "DEMO_MAX_DAILY_MESSAGES", 2)
    codes = [ask(client, project_id, headers).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_demo_token_expires_after_the_demo_lifetime(client, demo):
    import time

    import jwt

    token = demo[1]["Authorization"].split()[1]
    claims = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert claims["demo"] is True
    assert claims["exp"] - time.time() <= settings.DEMO_TOKEN_EXPIRE_MINUTES * 60


def test_normal_user_is_not_blocked(client, make_user):
    _, headers = make_user()
    body = [{"name": "a.txt", "mimeType": "text/plain", "size": 5}]
    assert client.post("/api/files", json=body, headers=headers).status_code == 200
