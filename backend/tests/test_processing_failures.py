from tests.helpers import upload_and_confirm


def first_file(client, headers, project_id):
    return client.get(f"/api/projects/{project_id}/files", headers=headers).json()[0]


def test_cp1252_csv_is_processed(client, make_user, aws_fakes):
    _, headers = make_user()
    data = "name,city\nJosé,Zürich\nRené,Málaga\n".encode("cp1252")
    project_id, _, _ = upload_and_confirm(client, aws_fakes, headers, "people.csv", data, "text/csv")
    assert first_file(client, headers, project_id)["status"] == "processed"


def test_corrupt_pdf_ends_in_error(client, make_user, aws_fakes):
    _, headers = make_user()
    project_id, _, _ = upload_and_confirm(
        client, aws_fakes, headers, "broken.pdf", b"this is not a pdf", "application/pdf"
    )
    file = first_file(client, headers, project_id)
    assert file["status"] == "error"
    assert "couldn't read" in file["error"]


def test_failed_enqueue_marks_files_errored(client, make_user, aws_fakes, monkeypatch):
    from src.settings import settings

    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    aws_fakes.sqs.fail = True
    _, headers = make_user()
    project_id, _, confirm = upload_and_confirm(client, aws_fakes, headers, "a.txt", b"hello world")
    assert confirm.status_code == 200
    file = first_file(client, headers, project_id)
    assert file["status"] == "error"
    assert "upload it again" in file["error"]
