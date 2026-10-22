from contextlib import contextmanager

from sqlalchemy import event

from src.database import engine
from src.features.chat.message_model import Citation, Message, MessageOwner
from src.features.files.file_model import Chunk, File
from tests.helpers import add_project_with_chunk


@contextmanager
def count_queries():
    statements = []

    def record(conn, cursor, statement, *args):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", record)


def seed_conversation(db, project_id, turns=30, citations=5):
    file = db.query(File).filter_by(project_id=project_id).one()
    chunks = [Chunk(file_id=file.id, content=f"chunk {i}", title=f"t{i}") for i in range(citations)]
    db.add_all(chunks)
    db.flush()
    for i in range(turns):
        db.add(Message(content=f"q{i}", owner=MessageOwner.user, project_id=project_id))
        answer = Message(content=f"a{i}", owner=MessageOwner.assistant, project_id=project_id)
        answer.chunks = chunks
        db.add(answer)
    db.commit()


def test_project_list_is_small_and_constant_cost(client, db, make_user):
    user, headers = make_user()
    ids = [add_project_with_chunk(db, user["id"]) for _ in range(3)]
    for project_id in ids:
        seed_conversation(db, project_id)

    with count_queries() as statements:
        res = client.get("/api/projects", headers=headers)
    assert res.status_code == 200
    # token user lookup + project list
    assert len(statements) <= 3, statements
    body = res.json()
    assert len(body) == 3
    assert set(body[0]) == {"id", "name"}


def test_project_detail_has_no_messages_or_files(client, db, make_user):
    user, headers = make_user()
    project_id = add_project_with_chunk(db, user["id"])
    seed_conversation(db, project_id)
    with count_queries() as statements:
        res = client.get(f"/api/projects/{project_id}", headers=headers)
    assert res.status_code == 200
    assert set(res.json()) == {"id", "name"}
    assert len(statements) <= 3


def test_message_page_loads_citations_without_n_plus_one(client, db, make_user):
    user, headers = make_user()
    project_id = add_project_with_chunk(db, user["id"])
    seed_conversation(db, project_id, turns=15)
    with count_queries() as statements:
        res = client.get(f"/api/projects/{project_id}/messages?limit=30", headers=headers)
    assert res.status_code == 200
    assert len(res.json()["messages"]) == 30
    assert len(statements) <= 8, len(statements)


def test_chat_response_loads_citations_in_a_constant_number_of_queries(client, db, make_user):
    user, headers = make_user()
    project_id = add_project_with_chunk(db, user["id"])
    res = client.post(
        f"/api/projects/{project_id}/messages", json={"content": "banana"}, headers=headers
    )
    assert res.status_code == 200
    assert res.json()["citations"][0]["fileName"] == "recipes.txt"
