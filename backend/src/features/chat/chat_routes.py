from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from src import analytics
from src.database import get_db
from src.exceptions import NotAuthorisedError, TooManyRequestsError
from src.features.auth import user_service
from src.features.auth.user_model import User
from src.features.chat import chat_service
from src.features.demo import demo_service
from src.features.chat.chat_schema import (
    MessageCreate,
    MessageResponse,
    PaginatedMessages,
)
from src.features.project import project_service
from src.limiter import chat_limit, limiter
from src.settings import settings

router = APIRouter(prefix="/api/projects/{project_id}/messages", tags=["Chat"])


@router.get("", response_model=PaginatedMessages)
def get_chat_messages(
    project_id: int,
    user: User = Depends(user_service.get_current_user),
    db: Session = Depends(get_db),
    before_id: int | None = None,
    limit: int | None = 30,
):
    project = project_service.get_project(db, project_id)
    if project.user_id != user.id:
        raise NotAuthorisedError("You must own this project to see its messages")

    return chat_service.get_messages(db, project_id, before_id=before_id, limit=limit)


@router.post("", response_model=MessageResponse)
@limiter.limit(chat_limit)
def send_chat_messsage(
    project_id: int,
    message: MessageCreate,
    request: Request,
    user: User = Depends(user_service.get_current_user),
    db: Session = Depends(get_db),
):
    project = project_service.get_project(db, project_id)
    if project.user_id != user.id:
        raise NotAuthorisedError("You must own this project to see its messages")

    total_message_this_month = chat_service.get_messages_this_month(db, user.id)
    message_limit = settings.MAX_MONTHLY_MESSAGES
    if total_message_this_month > message_limit:
        analytics.capture(
            "usage_limit_reached", user.id, user.is_demo, limit="messages"
        )
        if user.is_demo:
            raise TooManyRequestsError(
                f"The shared demo has reached its limit of {message_limit} messages. Please try again later."
            )
        raise TooManyRequestsError(
            f"Free accounts can only send {settings.MAX_MONTHLY_MESSAGES} per month."
        )
    message_response = chat_service.send_user_message(
        db, user.id, project_id, message.content, is_demo=user.is_demo
    )
    return message_response
