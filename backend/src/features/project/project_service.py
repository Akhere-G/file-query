from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from src.exceptions import BadRequestError, NotFoundError
from src.features.files.file_model import FileStatus, Project
from src.features.files.file_service import delete_object
from src.settings import settings


def get_projects(db: Session, user_id: int):
    stmt = select(Project).where(Project.user_id == user_id)
    return db.execute(stmt).scalars().all()


def get_project(
    db: Session,
    project_id: int,
    with_files: bool | None = False,
):
    stmt = select(Project).where(Project.id == project_id)

    if with_files:
        stmt = stmt.options(selectinload(Project.files))

    project = db.execute(stmt).scalar_one_or_none()
    if not project:
        raise NotFoundError("Project not found")
    return project


def get_owned_project(
    db: Session, project_id: int, user_id: int, with_files: bool | None = False
):
    """Another user's project looks exactly like a missing one (404, not 403)."""
    project = get_project(db, project_id, with_files=with_files)
    if project.user_id != user_id:
        raise NotFoundError("Project not found")
    return project


def create_project(db: Session, user_id: int, name: str):
    new_project = Project(name=name, user_id=user_id)
    db.add(new_project)
    db.flush()
    return new_project


def delete_project(db: Session, project_id: int):
    project = get_project(db, project_id, with_files=True)
    storage_keys = [file.storage_key for file in project.files]
    db.delete(project)
    db.commit()

    for key in storage_keys:
        delete_object(key)

    return project_id


def update_project(db: Session, project_id: int, new_name: str):
    stripped_name = new_name.strip()
    if not stripped_name:
        raise BadRequestError("Project name cannot be empty")
    if len(stripped_name) > 255:
        raise BadRequestError("Project name is too long")

    project = get_project(db, project_id)
    project.name = stripped_name
    db.commit()
    return project
