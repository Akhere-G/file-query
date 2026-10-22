from datetime import datetime, timedelta, timezone

import pytest

from src.features.files import file_service
from src.features.files.file_model import File, FileStatus
from src.settings import settings
from tests.helpers import upload_and_confirm


def statuses(client, headers, project_id):
    files = client.get(f"/api/projects/{project_id}/files", headers=headers).json()
    return [f["status"] for f in files]


@pytest.mark.parametrize("size", [0, -5])
def test_non_positive_sizes_rejected(client, make_user, size):
    _, headers = make_user()
    body = [{"name": "a.txt", "mimeType": "text/plain", "size": size}]
    assert client.post("/api/files", json=body, headers=headers).status_code == 422


def test_quota_overflow_at_confirm_leaves_no_pending_files(
    client, make_user, aws_fakes, monkeypatch
):
    monkeypatch.setattr(settings, "MAX_USER_STORAGE", 15)
    _, headers = make_user()
    body = [{"name": f"{i}.txt", "mimeType": "text/plain", "size": 5} for i in range(3)]
    res = client.post("/api/files", json=body, headers=headers)
    assert res.status_code == 200, res.text
    project_id = res.json()["projectId"]
    for file in res.json()["files"]:
        aws_fakes.s3.put(file["key"], b"x" * 10)  # larger than declared

    ids = [{"id": f["id"]} for f in res.json()["files"]]
    assert client.post("/api/files/confirm", json=ids, headers=headers).status_code == 200

    found = statuses(client, headers, project_id)
    assert "pending" not in found
    assert found.count("error") == 2
    assert len(aws_fakes.s3.deleted) == 2


def test_quota_check_at_upload(client, make_user, monkeypatch):
    monkeypatch.setattr(settings, "MAX_USER_STORAGE", 8)
    _, headers = make_user()
    body = [{"name": f"{i}.txt", "mimeType": "text/plain", "size": 5} for i in range(2)]
    assert client.post("/api/files", json=body, headers=headers).status_code == 400


def test_used_storage_is_summed_in_sql(client, db, make_user, aws_fakes):
    user, headers = make_user()
    upload_and_confirm(client, aws_fakes, headers, "a.txt", b"12345")
    upload_and_confirm(client, aws_fakes, headers, "b.txt", b"1234567")
    assert file_service.get_used_storage(db, user["id"]) == 12
    assert file_service.get_used_storage(db, user["id"] + 99) == 0


def test_deleting_a_pending_file_removes_its_object(client, make_user, aws_fakes):
    _, headers = make_user()
    res = client.post(
        "/api/files",
        json=[{"name": "a.txt", "mimeType": "text/plain", "size": 5}],
        headers=headers,
    )
    file = res.json()["files"][0]
    aws_fakes.s3.put(file["key"], b"12345")
    assert client.delete(f"/api/files/{file['id']}", headers=headers).status_code == 200
    assert file["key"] in aws_fakes.s3.deleted


def test_s3_failure_on_delete_does_not_fail_the_request(client, make_user, aws_fakes, monkeypatch):
    _, headers = make_user()
    project_id, file_id, _ = upload_and_confirm(client, aws_fakes, headers, "a.txt", b"hello")

    def boom(**kwargs):
        raise RuntimeError("s3 down")

    monkeypatch.setattr(aws_fakes.s3, "delete_object", boom)
    assert client.delete(f"/api/files/{file_id}", headers=headers).status_code == 200


def test_stale_pending_uploads_are_cleaned_up(client, db, make_user, aws_fakes):
    _, headers = make_user()
    res = client.post(
        "/api/files",
        json=[{"name": "a.txt", "mimeType": "text/plain", "size": 5}],
        headers=headers,
    )
    file_row = db.get(File, res.json()["files"][0]["id"])
    key = file_row.storage_key
    aws_fakes.s3.put(key, b"12345")

    assert file_service.delete_stale_pending_files(db, older_than_hours=24) == 0

    file_row.created_at = datetime.now(timezone.utc) - timedelta(hours=30)
    db.commit()
    assert file_service.delete_stale_pending_files(db, older_than_hours=24) == 1
    assert db.get(File, file_row.id) is None
    assert key in aws_fakes.s3.deleted
