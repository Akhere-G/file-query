from fastapi import APIRouter, Depends
from src.features.project.project_schema import ProjectResponse
from src.features.project import project_service
from src.database import get_db
from src.features.auth import user_service
from src.features.auth.user_model import User
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/projects", tags=["Projects"])


@router.get("", response_model=list[ProjectResponse])
def get_projects(
    user: User = Depends(user_service.get_current_user), db: Session = Depends(get_db)
):
    return project_service.get_projects(db, user.id)
