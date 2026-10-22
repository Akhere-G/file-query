"""Every resource route must refuse another user's data."""

import pytest

IDS = {"mimeType": "text/plain", "size": 5}


@pytest.fixture
def owned(client, make_user, aws_fakes):
    owner, owner_headers = make_user()
    res = client.post(
        "/api/files",
        json=[{"name": "a.txt", **IDS}],
        headers=owner_headers,
    )
    assert res.status_code == 200, res.text
    project_id = res.json()["projectId"]
    file_id = res.json()["files"][0]["id"]
    _, other_headers = make_user()
    return {"project": project_id, "file": file_id, "other": other_headers}


def test_other_user_cannot_read_or_change_project(client, owned):
    pid, h = owned["project"], owned["other"]
    assert client.get(f"/api/projects/{pid}", headers=h).status_code == 404
    assert client.get(f"/api/projects/{pid}/files", headers=h).status_code == 404
    assert client.get(f"/api/projects/{pid}/messages", headers=h).status_code == 404
    assert client.patch(f"/api/projects/{pid}", json={"name": "x"}, headers=h).status_code == 404
    assert client.delete(f"/api/projects/{pid}", headers=h).status_code == 404
    assert (
        client.post(f"/api/projects/{pid}/messages", json={"content": "hi"}, headers=h).status_code
        == 404
    )


def test_other_user_cannot_touch_file(client, owned):
    fid, h = owned["file"], owned["other"]
    assert client.get(f"/api/files/{fid}", headers=h).status_code == 404
    assert client.delete(f"/api/files/{fid}", headers=h).status_code == 404
    assert client.post("/api/files/confirm", json=[{"id": fid}], headers=h).status_code == 404


def test_other_user_cannot_upload_to_project(client, owned):
    res = client.post(
        f"/api/files?project_id={owned['project']}",
        json=[{"name": "b.txt", **IDS}],
        headers=owned["other"],
    )
    assert res.status_code == 404
