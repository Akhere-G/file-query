from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.orm import Session
from src import analytics
from src.database import get_db
from src.exceptions import NotFoundError, TooManyRequestsError
from src.features.auth.user_model import User
from src.features.auth.user_service import get_current_user
from src.features.demo.demo_guard import block_demo
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
import logging

logger = logging.getLogger(__name__)


@router.get("/{file_id}")
def get_file(
    file_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    file = file_service.get_owned_file(db, file_id, user.id)

    url = file_service.view_file_content(db, file_id)
    return {"file": FileResponse.model_validate(file), "url": url}


# TODO: rate limit based on no. projects and 20/hour
@router.post(
    "",
)
@limiter.limit("20/hour")
@block_demo
def upload_files(
    files_in: list[FileCreate],
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    project_id: int | None = None,
):
    if project_id is None:
        projects = project_service.get_projects(db, user.id)
        if len(projects) >= settings.MAX_PROJECTS_PER_USER:
            analytics.capture(
                "usage_limit_reached", user.id, user.is_demo, limit="projects"
            )
            raise TooManyRequestsError(
                f"Free accounts can only have up to {settings.MAX_PROJECTS_PER_USER} projects"
            )
        project = project_service.create_project(db, user.id, "New Project")
        project_id = project.id
        analytics.capture(
            "project_created",
            user.id,
            user.is_demo,
            source="first_upload",
            project_count=len(projects) + 1,
        )
    else:
        project_service.get_owned_project(db, project_id, user.id)

    files = file_service.create_files(db, user.id, project_id, files_in)
    return {"files": file_service.get_presigned_post(files), "projectId": project_id}


@router.post("/confirm", response_model=list[FileResponse])
@block_demo
def confirm_uploads(
    confirmed_files: list[ConfirmUploadRequest],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    file_ids = [file.id for file in confirmed_files]
    files = [
        file
        for file in file_service.get_files_by_ids(db, file_ids)
        if file.project.user_id == user.id
    ]
    if len(files) != len(confirmed_files):
        missing = len(confirmed_files) - len(files)
        raise NotFoundError(f"{missing} file(s) could not be found")

    files = file_service.confirm_uploads(db, user.id, confirmed_files)
    if settings.ENVIRONMENT == "production":
        logger.info("enqueuing files")
        try:
            enqueue_files(files)
        except Exception:
            logger.exception("Could not enqueue files")
            file_service.mark_files_error(
                db, files, "Could not start processing this file. Please upload it again."
            )
    else:
        logger.info("local file processing")
        background_tasks.add_task(process_files_locally, files)
    return files


@router.delete("/{file_id:int}")
@block_demo
def delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    file_service.get_owned_file(db, file_id, user.id)
    return file_service.delete_file(db, file_id)
