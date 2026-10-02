from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.database import get_db
from src.features.auth import user_service
from src.features.auth.user_model import User
from src.features.chat import chat_service
from src.features.project import project_service
from src.exceptions import NotAuthorisedError
from src.features.chat.chat_schema import MessageCreate, MessageResponse

router = APIRouter(prefix="/api/projects/{project_id}/messages", tags=["Chat"])


@router.get("", response_model=list[MessageResponse])
def get_chat_messages(
    project_id: int,
    user: User = Depends(user_service.get_current_user),
    db: Session = Depends(get_db),
):
    project = project_service.get_project(db, project_id)
    if project.user_id != user.id:
        raise NotAuthorisedError("You must own this project to see its messages")

    return chat_service.get_messages(db, project_id)


@router.post("", response_model=MessageResponse)
def send_chat_messsage(
    project_id: int,
    message: MessageCreate,
    user: User = Depends(user_service.get_current_user),
    db: Session = Depends(get_db),
):
    project = project_service.get_project(db, project_id)
    if project.user_id != user.id:
        raise NotAuthorisedError("You must own this project to see its messages")
    message_response = chat_service.send_user_message(
        db, user.id, project_id, message.content
    )
    return message_response
