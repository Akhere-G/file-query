from src.features.files.file_model import FileStatus
from src.schemas import BaseModel


class FileBase(BaseModel):
    name: str
    mime_type: str
    size: int


class FileCreate(FileBase):
    pass


class FileResponse(FileBase):
    id: int
    error: str | None
    project_id: str
    storage_key: str
    status: FileStatus
