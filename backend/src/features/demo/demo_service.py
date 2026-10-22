from sqlalchemy.orm import Session
from src.exceptions import BadRequestError
from src.features.auth.user_model import User
from src.features.files.file_schema import FileCreate
from src.features.files.file_service import get_used_storage
from src.settings import settings

DEMO_LIMIT_HINT = "This is a shared demo account."


def enforce_upload_limits(db: Session, user: User, files_in: list[FileCreate]):
    for file in files_in:
        if file.size > settings.MAX_FILE_SIZE:
            max_mb = settings.MAX_FILE_SIZE
            raise BadRequestError(
                f"{DEMO_LIMIT_HINT} Files must be {max_mb} MB or smaller."
            )

    used_storage = get_used_storage(db, user.id)
    upload_size = sum(file.size for file in files_in)
    if used_storage + upload_size > settings.MAX_USER_STORAGE:
        raise BadRequestError(
            f"{DEMO_LIMIT_HINT} Its storage is full. Delete files to upload more."
        )
