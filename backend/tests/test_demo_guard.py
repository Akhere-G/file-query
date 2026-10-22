import time

import pytest

from src.features.auth.user_model import User
from src.features.auth.user_service import get_password_hash
from src.features.chat.message_model import Message
from src.features.demo import demo_service
from src.features.demo.demo_guard import block_demo
from src.settings import settings
from tests.helpers import add_project_with_chunk

SECRET = {"X-Internal-Secret": "test-internal-secret", "X-Client-IP": "203.0.113.50"}


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
    res = client.post("/api/auth/demo", headers=SECRET)
    assert res.status_code == 200
    headers = {"Authorization": f"Bearer {res.json()['access_token']}"}
    return project_id, headers


def test_demo_can_read(client, demo):
    project_id, headers = demo
    assert client.get("/api/projects", headers=headers).status_code == 200
    assert client.get(f"/api/projects/{project_id}/files", headers=headers).status_code == 200
    assert client.get(f"/api/projects/{project_id}/messages", headers=headers).status_code == 200


def test_demo_cannot_change_anything(client, db, demo):
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
    # nothing was deleted
    assert client.get(f"/api/projects/{project_id}", headers=headers).status_code == 200


def test_demo_chat_answers_without_saving(client, db, demo):
    project_id, headers = demo
    res = client.post(
        f"/api/projects/{project_id}/messages", json={"content": "banana"}, headers=headers
    )
    assert res.status_code == 200, res.text
    assert res.json()["id"] < 0
    assert res.json()["citations"]
    assert db.query(Message).count() == 0


def test_demo_token_is_short_lived(client, demo):
    import jwt

    _, headers = demo
    token = headers["Authorization"].split()[1]
    claims = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert claims["demo"] is True
    assert claims["exp"] - time.time() <= settings.DEMO_TOKEN_EXPIRE_MINUTES * 60


class FakeRedis:
    def __init__(self):
        self.counts = {}

    def incr(self, key):
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    def expire(self, key, seconds):
        pass


def test_demo_daily_chat_cap(client, demo, monkeypatch):
    project_id, headers = demo
    fake = FakeRedis()
    monkeypatch.setattr(demo_service, "_redis", lambda: fake)
    monkeypatch.setattr(settings, "DEMO_MAX_DAILY_MESSAGES", 2)
    codes = [
        client.post(
            f"/api/projects/{project_id}/messages", json={"content": "banana"}, headers=headers
        ).status_code
        for _ in range(3)
    ]
    assert codes == [200, 200, 429]


def test_demo_chat_is_limited_per_ip(client, demo):
    project_id, headers = demo
    codes = []
    for _ in range(11):
        res = client.post(
            f"/api/projects/{project_id}/messages",
            json={"content": "banana"},
            headers={**headers, **SECRET},
        )
        codes.append(res.status_code)
    assert codes[-1] == 429


def test_block_demo_rejects_unprotectable_routes():
    def no_user(x):
        return x

    with pytest.raises(TypeError):
        block_demo(no_user)

    async def async_route(user: User):
        return user

    with pytest.raises(TypeError):
        block_demo(async_route)


def test_normal_user_is_not_blocked(client, make_user):
    _, headers = make_user()
    body = [{"name": "a.txt", "mimeType": "text/plain", "size": 5}]
    assert client.post("/api/files", json=body, headers=headers).status_code == 200
