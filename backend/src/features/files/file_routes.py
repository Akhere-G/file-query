from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.database import get_db
from src.exceptions import BadRequestError, NotAuthorisedError, NotFoundError
from src.features.auth.user_model import User
from src.features.auth.user_service import get_current_user
from src.features.files import file_service
from src.features.files.file_processing_service import enqueue_files
from src.features.files.file_schema import (
    ConfirmUploadRequest,
    FileCreate,
    FileResponse,
)

router = APIRouter(prefix="/api/files", tags=["Files"])


@router.get("", response_model=FileResponse)
def get_files(
    project_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not project_id:
        return BadRequestError("Project is is missing!")

    project = file_service.get_project(db, project_id)
    if project.user_id != user.id:
        raise NotAuthorisedError("You must own this project to view its files")

    return file_service.get_files(db, project_id)


@router.post(
    "",
)
def upload_files(
    files_in: list[FileCreate],
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    project_id: int | None = None,
):
    if project_id is None:
        project = file_service.create_project(db, user.id, "New Project")
        project_id = project.id
    else:
        project = file_service.get_project(db, project_id)
        if project.user_id != user.id:
            raise NotAuthorisedError("You are not allowed to upload to this project")

    files = file_service.create_files(db, user.id, project_id, files_in)
    return {"files": file_service.get_presigned_post(files), "projectId": project_id}


@router.post("/confirm")
def confirm_uploads(
    confirmed_files: list[ConfirmUploadRequest],
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    file_ids = [file.id for file in confirmed_files]
    files = file_service.get_files_by_ids(db, file_ids)
    if len(files) != len(confirmed_files):
        missing = len(confirmed_files) - len(files)
        raise NotFoundError(f"{missing} file(s) could not be found")

    for file in files:
        if file.project.user_id != user.id:
            raise NotAuthorisedError("Not allowed to edit this file")

    files = file_service.confirm_uploads(db, user.id, confirmed_files)
    enqueue_files(files)
    return files
