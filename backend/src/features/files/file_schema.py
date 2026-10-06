from pydantic import field_validator
from src.features.files.file_model import FileStatus
from src.schemas import BaseModel
from src.settings import settings

MAX_FILE_SIZE = settings.MAX_FILE_SIZE
MAX_USER_STORAGE = settings.MAX_USER_STORAGE

accepted_mime_types = {
    "application/msword": ".docx",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".doc",
    "text/plain": ".txt",
    "application/pdf": ".pdf",
    "text/csv": ".csv",
    "text/markdown": ".md",
}


class FileBase(BaseModel):
    name: str
    mime_type: str
    size: int

    @field_validator("size")
    @classmethod
    def validate_size(cls, v):
        if v >= MAX_FILE_SIZE:
            raise ValueError("Files must be less than 500mb")
        return v

    @field_validator("mime_type")
    @classmethod
    def validate_mime_type(cls, v):
        if v not in accepted_mime_types:
            raise ValueError(
                f"Files must one of {', '.join(accepted_mime_types.values())}"
            )
        return v


class FileCreate(FileBase):
    pass


class FileResponse(FileBase):
    id: int
    error: str | None
    project_id: int
    storage_key: str
    status: FileStatus


class ConfirmUploadRequest(BaseModel):
    id: int
    error: str | None = None
