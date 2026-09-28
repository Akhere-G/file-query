from pydantic import field_validator
from src.features.files.file_model import FileStatus
from src.schemas import BaseModel

max_file_size = 1024 * 1024 * 500
max_user_storage = 1024 * 1024 * 1024 * 2
accepted_mime_types = [
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "application/pdf",
]


class FileBase(BaseModel):
    name: str
    mime_type: str
    size: int

    @field_validator("size")
    @classmethod
    def validate_size(cls, v):
        if v >= max_file_size:
            raise ValueError("Files must be less than 500mb")
        return v

    @field_validator("mime_type")
    @classmethod
    def validate_mime_type(cls, v):
        if v not in accepted_mime_types:
            raise ValueError(f"Files must one of {', '.join(accepted_mime_types)}")
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
    error: str | None
