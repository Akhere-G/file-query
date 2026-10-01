from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.database import get_db
from src.exceptions import BadRequestError, NotAuthorisedError
from src.features.auth import user_service
from src.features.auth.user_model import User
from src.features.files import file_service
from src.features.files.file_schema import FileResponse
from src.features.project import project_service
from src.features.project.project_schema import ProjectResponse

router = APIRouter(prefix="/api/projects", tags=["Projects"])


@router.get("", response_model=list[ProjectResponse])
def get_projects(
    user: User = Depends(user_service.get_current_user), db: Session = Depends(get_db)
):
    return project_service.get_projects(db, user.id)


@router.get("/{project_id:int}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    user: User = Depends(user_service.get_current_user),
    db: Session = Depends(get_db),
):
    project = project_service.get_project(
        db, project_id, with_messages=True, with_files=True
    )
    if project.user_id != user.id:
        raise NotAuthorisedError("You cannot access this project")
    return project


@router.get("/{project_id:int}/files", response_model=FileResponse)
def get_files(
    project_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(user_service.get_current_user),
):
    if not project_id:
        return BadRequestError("Project is is missing!")

    project = project_service.get_project(db, project_id)
    if project.user_id != user.id:
        raise NotAuthorisedError("You must own this project to view its files")

    return file_service.get_files(db, project_id)
