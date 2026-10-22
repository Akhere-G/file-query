import reprocess_all
from src.features.files.file_model import Chunk
from src.settings import settings
from tests.helpers import add_project_with_chunk


def run(monkeypatch, *args):
    monkeypatch.setattr("sys.argv", ["reprocess_all", *args])
    return reprocess_all.main()


def test_refuses_to_run_in_production(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    assert run(monkeypatch, "--apply") == 2


def test_changes_nothing_without_apply(client, db, make_user, monkeypatch):
    user, _ = make_user()
    add_project_with_chunk(db, user["id"])
    assert run(monkeypatch) == 0
    assert db.query(Chunk).count() == 1
