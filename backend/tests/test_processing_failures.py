import pytest

from src.features.files.file_model import FileStatus
from tests.helpers import upload_and_confirm


def file_state(client, headers, project_id):
    return client.get(f"/api/projects/{project_id}/files", headers=headers).json()[0]


def test_cp1252_csv_is_processed(client, make_user, aws_fakes):
    _, headers = make_user()
    data = "name,city\nJosé,Zürich\nRené,Málaga\n".encode("cp1252")
    project_id, _, _ = upload_and_confirm(
        client, aws_fakes, headers, "people.csv", data, mime="text/csv"
    )
    assert file_state(client, headers, project_id)["status"] == "processed"


def test_corrupt_pdf_ends_in_error_not_processing(client, make_user, aws_fakes):
    _, headers = make_user()
    project_id, _, _ = upload_and_confirm(
        client, aws_fakes, headers, "broken.pdf", b"this is not a pdf", mime="application/pdf"
    )
    state = file_state(client, headers, project_id)
    assert state["status"] == FileStatus.error.value
    assert "couldn't read" in state["error"]
    assert "Traceback" not in state["error"] and "/" not in state["error"]


def test_failed_enqueue_marks_files_errored(client, make_user, aws_fakes, monkeypatch):
    from src.settings import settings

    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    aws_fakes.sqs.fail = True
    _, headers = make_user()
    project_id, _, confirm = upload_and_confirm(
        client, aws_fakes, headers, "a.txt", b"hello world"
    )
    assert confirm.status_code == 200
    state = file_state(client, headers, project_id)
    assert state["status"] == "error"
    assert "upload it again" in state["error"]


def test_enqueue_success_sends_job(client, make_user, aws_fakes, monkeypatch):
    from src.settings import settings

    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    _, headers = make_user()
    upload_and_confirm(client, aws_fakes, headers, "a.txt", b"hello world")
    assert len(aws_fakes.sqs.sent) == 1
    assert aws_fakes.sqs.sent[0]["rename_project"] is True
