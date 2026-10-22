"""Builders for database fixtures."""

from src.features.files.file_model import Chunk, File, FileStatus, Project


def add_project_with_chunk(db, user_id: int, text: str = "banana bread needs ripe bananas"):
    project = Project(name="Recipes", user_id=user_id)
    db.add(project)
    db.flush()
    file = File(
        name="recipes.txt",
        mime_type="text/plain",
        size=len(text),
        status=FileStatus.processed,
        storage_key=f"test/{project.id}/recipes",
        project_id=project.id,
    )
    db.add(file)
    db.flush()
    db.add(Chunk(file_id=file.id, content=text, title="Banana bread"))
    db.commit()
    return project.id


def upload_and_confirm(client, aws_fakes, headers, name, data, mime="text/plain", project_id=None):
    """Upload through the API, put the bytes in fake S3 and confirm (processes locally)."""
    url = "/api/files" + (f"?project_id={project_id}" if project_id else "")
    res = client.post(
        url, json=[{"name": name, "mimeType": mime, "size": len(data)}], headers=headers
    )
    assert res.status_code == 200, res.text
    file = res.json()["files"][0]
    aws_fakes.s3.put(file["key"], data)
    confirm = client.post("/api/files/confirm", json=[{"id": file["id"]}], headers=headers)
    return res.json()["projectId"], file["id"], confirm
