from src.features.files.file_model import Chunk, File, FileStatus, Project


def add_project_with_chunk(db, user_id, text="banana bread needs ripe bananas"):
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
    url = "/api/files" + (f"?project_id={project_id}" if project_id else "")
    res = client.post(
        url, json=[{"name": name, "mimeType": mime, "size": len(data)}], headers=headers
    )
    assert res.status_code == 200, res.text
    file = res.json()["files"][0]
    aws_fakes.s3.put(file["key"], data)
    confirm = client.post("/api/files/confirm", json=[{"id": file["id"]}], headers=headers)
    return res.json()["projectId"], file["id"], confirm


def add_project(db, user_id, name="Project"):
    project = Project(name=name, user_id=user_id)
    db.add(project)
    db.commit()
    return project.id


def add_file_with_chunks(db, project_id, texts, name="doc.md", embed=True, status=FileStatus.processed):
    """Insert a file and one chunk per text. `embed` uses the same bag-of-words embedder as
    the semantic fakes, so query/chunk similarity is deterministic."""
    from uuid import uuid4

    from tests.fakes import bag_of_words_vector

    file = File(
        name=name,
        mime_type="text/markdown",
        size=sum(len(t) for t in texts) or 1,
        status=status,
        storage_key=f"test/{project_id}/{uuid4()}",
        project_id=project_id,
    )
    db.add(file)
    db.flush()
    chunks = [
        Chunk(
            file_id=file.id,
            content=text,
            title=text.split(".")[0][:100],
            embedding=bag_of_words_vector(text) if embed else None,
        )
        for text in texts
    ]
    db.add_all(chunks)
    db.commit()
    return file.id, [chunk.id for chunk in chunks]
