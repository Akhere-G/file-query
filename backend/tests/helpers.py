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
