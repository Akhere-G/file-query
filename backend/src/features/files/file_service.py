from sqlalchemy import select
from sqlalchemy.orm import Session
from src.exceptions import BadRequestError, NotFoundError
from src.features.files.file_model import File, FileStatus, Project
from src.features.files.file_schema import FileCreate


def get_projects(db: Session, user_id: int):
    stmt = select(Project).where(Project.user_id == user_id)
    return db.execute(stmt).scalars().all()


def get_project(db: Session, project_id: int):
    stmt = select(Project).where(Project.id == project_id)
    return db.execute(stmt).scalar_one_or_none()


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


def get_files(db: Session, project_id: int):
    stmt = select(File).where(File.project_id == project_id)
    return db.execute(stmt).scalars().all()


def get_files_by_ids(db: Session, file_ids: list[int]):
    stmt = select(File).where(File.id.in_(file_ids))
    return db.execute(stmt).scalars().all()


def get_file(db: Session, file_id: int):
    stmt = select(File).where(File.id == file_id)
    file = db.execute(stmt).scalar_one_or_none()
    if not file:
        raise NotFoundError("File not found")
    return file


def view_file_content(db: Session, file_id: int):
    file = get_file(db, file_id)

    # TODO: use storage key and return presigned url


def create_file(db: Session, project_id: int, file_in: FileCreate):
    new_file = File(
        name=file_in.name,
        mime_type=file_in.mime_type,
        size=file_in.size,
        project_id=project_id,
    )
    db.add(new_file)
    db.commit()
    return new_file


def create_files(db: Session, project_id: int, files_in: list[FileCreate]):
    res = []
    for file in files_in:
        new_file = File(
            name=file.name,
            mime_type=file.mime_type,
            size=file.size,
            project_id=project_id,
        )
        res.append(new_file)
    db.add_all(res)
    db.commit()
    return res


def get_presigned_url():
    pass


def add_storage_keys(db: Session, file_ids: list[int], new_storage_keys: list[str]):
    files = get_files_by_ids(db, file_ids)

    for i, file in enumerate(files):
        if file.storage_key:
            db.rollback()
            raise BadRequestError("File already uploaded")

        file.storage_key = new_storage_keys[i]
        file.status = FileStatus.processing
    db.commit()
    return files


def add_embbedding(db: Session, file_id: int):
    file = get_file(db, file_id)
    if file.status == FileStatus.pending:
        raise BadRequestError("Cannot create on unuploaded file")
    if file.status == FileStatus.processed:
        raise BadRequestError("Embeddings already created")

    # TODO: Extract text
    # TODO: Create Chunks
    # TODO: Create embeddings


def delete_file(db: Session, file_id: int):
    file = get_file(db, file_id)
    db.delete(file)
    db.commit()
    # TODO: delete on s3
    return file_id
