import pytest

from src.features.files import file_service
from src.settings import settings
from tests.helpers import upload_and_confirm


@pytest.mark.parametrize("size", [0, -5])
def test_non_positive_sizes_rejected(client, make_user, size):
    _, headers = make_user()
    body = [{"name": "a.txt", "mimeType": "text/plain", "size": size}]
    assert client.post("/api/files", json=body, headers=headers).status_code == 422


def test_over_quota_files_are_all_errored_at_confirm(client, make_user, aws_fakes, monkeypatch):
    monkeypatch.setattr(settings, "MAX_USER_STORAGE", 15)
    _, headers = make_user()
    body = [{"name": f"{i}.txt", "mimeType": "text/plain", "size": 5} for i in range(3)]
    res = client.post("/api/files", json=body, headers=headers)
    for file in res.json()["files"]:
        aws_fakes.s3.put(file["key"], b"x" * 10)

    ids = [{"id": file["id"]} for file in res.json()["files"]]
    assert client.post("/api/files/confirm", json=ids, headers=headers).status_code == 200

    files = client.get(f"/api/projects/{res.json()['projectId']}/files", headers=headers).json()
    statuses = [file["status"] for file in files]
    assert "pending" not in statuses
    assert statuses.count("error") == 2
    assert len(aws_fakes.s3.deleted) == 2


def test_quota_is_checked_at_upload(client, make_user, monkeypatch):
    monkeypatch.setattr(settings, "MAX_USER_STORAGE", 8)
    _, headers = make_user()
    body = [{"name": f"{i}.txt", "mimeType": "text/plain", "size": 5} for i in range(2)]
    assert client.post("/api/files", json=body, headers=headers).status_code == 400


def test_used_storage_sums_in_sql(client, db, make_user, aws_fakes):
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


def test_deleting_a_project_removes_pending_objects_too(client, make_user, aws_fakes):
    _, headers = make_user()
    res = client.post(
        "/api/files",
        json=[{"name": "a.txt", "mimeType": "text/plain", "size": 5}],
        headers=headers,
    )
    file = res.json()["files"][0]
    aws_fakes.s3.put(file["key"], b"12345")
    assert client.delete(f"/api/projects/{res.json()['projectId']}", headers=headers).status_code == 200
    assert file["key"] in aws_fakes.s3.deleted
