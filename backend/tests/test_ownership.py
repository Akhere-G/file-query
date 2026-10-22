import pytest

FILE = {"mimeType": "text/plain", "size": 5}


@pytest.fixture
def owned(client, make_user):
    _, owner_headers = make_user()
    res = client.post("/api/files", json=[{"name": "a.txt", **FILE}], headers=owner_headers)
    assert res.status_code == 200, res.text
    _, other_headers = make_user()
    return {
        "project": res.json()["projectId"],
        "file": res.json()["files"][0]["id"],
        "other": other_headers,
    }


def test_other_user_cannot_read_or_change_project(client, owned):
    project, headers = owned["project"], owned["other"]
    assert client.get(f"/api/projects/{project}", headers=headers).status_code == 404
    assert client.get(f"/api/projects/{project}/files", headers=headers).status_code == 404
    assert client.get(f"/api/projects/{project}/messages", headers=headers).status_code == 404
    assert client.patch(f"/api/projects/{project}", json={"name": "x"}, headers=headers).status_code == 404
    assert client.delete(f"/api/projects/{project}", headers=headers).status_code == 404
    res = client.post(f"/api/projects/{project}/messages", json={"content": "hi"}, headers=headers)
    assert res.status_code == 404


def test_other_user_cannot_touch_file(client, owned):
    file, headers = owned["file"], owned["other"]
    assert client.get(f"/api/files/{file}", headers=headers).status_code == 404
    assert client.delete(f"/api/files/{file}", headers=headers).status_code == 404
    assert client.post("/api/files/confirm", json=[{"id": file}], headers=headers).status_code == 404


def test_other_user_cannot_upload_to_project(client, owned):
    res = client.post(
        f"/api/files?project_id={owned['project']}",
        json=[{"name": "b.txt", **FILE}],
        headers=owned["other"],
    )
    assert res.status_code == 404
