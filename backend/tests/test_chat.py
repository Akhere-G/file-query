import pytest

from src.features.chat.message_model import Message
from src.settings import settings
from tests.helpers import add_project_with_chunk


@pytest.fixture
def chat_project(client, db, make_user):
    user, headers = make_user()
    project_id = add_project_with_chunk(db, user["id"])
    return project_id, headers


def ask(client, project_id, headers, content="banana"):
    return client.post(
        f"/api/projects/{project_id}/messages", json={"content": content}, headers=headers
    )


def test_answer_is_saved_with_question(client, db, chat_project):
    project_id, headers = chat_project
    res = ask(client, project_id, headers)
    assert res.status_code == 200, res.text
    assert res.json()["owner"] == "assistant"
    assert res.json()["citations"], "retrieved chunk should be cited"
    owners = [m.owner.value for m in db.query(Message).order_by(Message.id)]
    assert owners == ["user", "assistant"]


def test_empty_and_oversize_messages_rejected(client, chat_project):
    project_id, headers = chat_project
    assert ask(client, project_id, headers, "   ").status_code == 422
    too_long = "x" * (settings.MAX_MESSAGE_LENGTH + 1)
    assert ask(client, project_id, headers, too_long).status_code == 422


def test_failed_generation_saves_nothing(client, db, chat_project, aws_fakes, monkeypatch):
    project_id, headers = chat_project

    def boom(**kwargs):
        raise RuntimeError("bedrock down")

    monkeypatch.setattr(aws_fakes.bedrock, "converse", boom)
    res = ask(client, project_id, headers)
    assert res.status_code == 500
    assert db.query(Message).count() == 0


def test_monthly_limit_is_enforced_at_the_limit(client, chat_project, monkeypatch):
    project_id, headers = chat_project
    monkeypatch.setattr(settings, "MAX_MONTHLY_MESSAGES", 2)
    assert ask(client, project_id, headers).status_code == 200
    assert ask(client, project_id, headers).status_code == 200
    assert ask(client, project_id, headers).status_code == 429


@pytest.mark.parametrize("limit", [-5, 0, 1, 500])
def test_message_listing_handles_odd_limits(client, chat_project, limit):
    project_id, headers = chat_project
    ask(client, project_id, headers)
    res = client.get(f"/api/projects/{project_id}/messages?limit={limit}", headers=headers)
    assert res.status_code == 200
