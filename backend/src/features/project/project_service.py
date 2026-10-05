from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from src.exceptions import BadRequestError, NotFoundError
from src.features.files.file_model import FileStatus, Project
from src.features.files.file_service import get_s3_client
from src.settings import settings

MAX_PROJECTS_PER_USER = 3


def get_projects(db: Session, user_id: int):
    stmt = select(Project).where(Project.user_id == user_id)
    return db.execute(stmt).scalars().all()


def get_project(
    db: Session,
    project_id: int,
    with_files: bool | None = False,
    with_messages: bool | None = False,
):
    stmt = select(Project).where(Project.id == project_id)

    if with_files:
        stmt = stmt.options(selectinload(Project.files))

    if with_messages:
        stmt = stmt.options(selectinload(Project.messages))

    project = db.execute(stmt).scalar_one_or_none()
    if not project:
        raise NotFoundError("Project not found")
    return project


def create_project(db: Session, user_id: int, name: str):
    new_project = Project(name=name, user_id=user_id)
    db.add(new_project)
    db.flush()
    return new_project


def delete_project(db: Session, project_id: int):
    project = get_project(db, project_id, with_files=True)
    storage_keys = [
        file.storage_key
        for file in project.files
        if file.status in [FileStatus.processing, FileStatus.processed]
    ]
    db.delete(project)
    db.commit()

    if storage_keys:
        s3_client = get_s3_client()
        for key in storage_keys:
            s3_client.delete_object(Bucket=settings.AWS_BUCKET_NAME, Key=key)

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
