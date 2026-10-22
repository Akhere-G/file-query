import pytest

from src.scripts import add_titles, reprocess_all
from src.settings import settings
from tests.helpers import add_project_with_chunk


def run(module, monkeypatch, *args):
    monkeypatch.setattr("sys.argv", [module.__name__, *args])
    return module.main()


def test_reprocess_all_refuses_production(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    assert run(reprocess_all, monkeypatch, "--apply") == 2


def test_reprocess_all_changes_nothing_without_apply(client, db, make_user, monkeypatch):
    user, _ = make_user()
    add_project_with_chunk(db, user["id"])
    from src.features.files.file_model import Chunk

    assert run(reprocess_all, monkeypatch) == 0
    assert db.query(Chunk).count() == 1


def test_add_titles_backfills_only_with_apply(client, db, make_user, monkeypatch):
    from src.features.files.file_model import Chunk

    user, _ = make_user()
    add_project_with_chunk(db, user["id"], "Bananas are yellow. They grow in bunches.")
    chunk = db.query(Chunk).one()
    chunk.title = None
    db.commit()

    assert run(add_titles, monkeypatch) == 0
    db.expire_all()
    assert db.query(Chunk).one().title is None

    assert run(add_titles, monkeypatch, "--apply") == 0
    db.expire_all()
    assert db.query(Chunk).one().title == "Bananas are yellow."
