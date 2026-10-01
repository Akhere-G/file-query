from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from src.exceptions import NotFoundError
from src.features.files.file_model import Project


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
    db.commit()
    return new_project


def delete_project(db: Session, project_id: int):
    project = get_project(db, project_id)
    if not project:
        raise NotFoundError("Project not found")
    db.delete(project)
    db.commit()
    return project_id


def update_project(db: Session, project_id: int, new_name: str):
    project = get_project(db, project_id)
    if not project:
        raise NotFoundError("Project not found")
    project.name = new_name
    db.commit()
    return project
