from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.database import get_db
from src.exceptions import BadRequestError
from src.features.auth import user_service
from src.features.auth.user_model import User
from src.features.demo.demo_guard import block_demo
from src.features.files import file_service
from src.features.files.file_schema import FileResponse
from src.features.project import project_service
from src.features.project.project_schema import ProjectSummary, RenameProjectRequest

router = APIRouter(prefix="/api/projects", tags=["Projects"])


@router.get("", response_model=list[ProjectSummary])
def get_projects(
    user: User = Depends(user_service.get_current_user), db: Session = Depends(get_db)
):
    return project_service.get_projects(db, user.id)


@router.get("/{project_id:int}", response_model=ProjectSummary)
def get_project(
    project_id: int,
    user: User = Depends(user_service.get_current_user),
    db: Session = Depends(get_db),
):
    return project_service.get_owned_project(db, project_id, user.id)


@router.get("/{project_id:int}/files", response_model=list[FileResponse])
def get_files(
    project_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(user_service.get_current_user),
):
    if not project_id:
        raise BadRequestError("Project is is missing!")

    project_service.get_owned_project(db, project_id, user.id)
    return file_service.get_files(db, project_id)


@router.patch("/{project_id:int}", response_model=ProjectSummary)
@block_demo
def rename_project(
    project_id: int,
    body: RenameProjectRequest,
    user: User = Depends(user_service.get_current_user),
    db: Session = Depends(get_db),
):
    project_service.get_owned_project(db, project_id, user.id)
    return project_service.update_project(db, project_id, body.name)


@router.delete("/{project_id:int}")
@block_demo
def delete_project(
    project_id: int,
    user: User = Depends(user_service.get_current_user),
    db: Session = Depends(get_db),
):
    project_service.get_owned_project(db, project_id, user.id)
    return {"id": project_service.delete_project(db, project_id)}
