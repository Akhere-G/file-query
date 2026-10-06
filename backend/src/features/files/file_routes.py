from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.orm import Session
from src.database import get_db
from src.exceptions import NotAuthorisedError, NotFoundError, TooManyRequestsError
from src.features.auth.user_model import User
from src.features.auth.user_service import get_current_user
from src.features.files import file_service
from src.features.files.file_processing_service import (
    enqueue_files,
    process_files_locally,
)
from src.features.files.file_schema import (
    ConfirmUploadRequest,
    FileCreate,
    FileResponse,
)
from src.features.project import project_service
from src.limiter import limiter
from src.settings import settings

router = APIRouter(prefix="/api/files", tags=["Files"])


@router.get("/{file_id}")
def get_file(
    file_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    file = file_service.get_file(db, file_id)

    if file.project.user_id != user.id:
        raise NotAuthorisedError("Not allowed to view this file")

    url = file_service.view_file_content(db, file_id)
    return {"file": FileResponse.model_validate(file), "url": url}


# TODO: rate limit based on no. projects and 20/hour
@limiter.limit("20/hour")
@router.post(
    "",
)
def upload_files(
    files_in: list[FileCreate],
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    project_id: int | None = None,
):
    if project_id is None:
        projects = project_service.get_projects(db, user.id)
        if len(projects) >= project_service.MAX_PROJECTS_PER_USER:
            raise TooManyRequestsError(
                f"Free accounts can only have up to {project_service.MAX_PROJECTS_PER_USER} projects"
            )
        project = project_service.create_project(db, user.id, "New Project")
        project_id = project.id
    else:
        project = project_service.get_project(db, project_id)
        if project.user_id != user.id:
            raise NotAuthorisedError("You are not allowed to upload to this project")

    files = file_service.create_files(db, user.id, project_id, files_in)
    return {"files": file_service.get_presigned_post(files), "projectId": project_id}


@router.post("/confirm")
def confirm_uploads(
    confirmed_files: list[ConfirmUploadRequest],
    background_tasks: BackgroundTasks,
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
    if settings.ENVIRONMENT == "production":
        enqueue_files(files)
    else:
        background_tasks.add_task(process_files_locally, files)
    return files


@router.delete("/{file_id:int}")
def delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    file = file_service.get_file(db, file_id)
    if file.project.user_id != user.id:
        raise NotAuthorisedError("Not allowed to delete this file")
    return file_service.delete_file(db, file_id)
