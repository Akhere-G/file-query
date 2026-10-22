from contextlib import contextmanager

from sqlalchemy import event

from src.database import engine
from src.features.chat.message_model import Message, MessageOwner
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


def add_conversation(db, project_id, turns=30, citations=5):
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


def test_project_list_does_not_load_messages_or_files(client, db, make_user):
    user, headers = make_user()
    for _ in range(3):
        add_conversation(db, add_project_with_chunk(db, user["id"]))

    with count_queries() as statements:
        res = client.get("/api/projects", headers=headers)

    assert res.status_code == 200
    assert len(statements) <= 3
    assert all(set(project) == {"id", "name"} for project in res.json())


def test_project_detail_does_not_load_messages_or_files(client, db, make_user):
    user, headers = make_user()
    project_id = add_project_with_chunk(db, user["id"])
    add_conversation(db, project_id)

    with count_queries() as statements:
        res = client.get(f"/api/projects/{project_id}", headers=headers)

    assert res.status_code == 200
    assert set(res.json()) == {"id", "name"}
    assert len(statements) <= 3
