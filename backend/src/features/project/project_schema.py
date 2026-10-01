from src.features.files.file_schema import FileResponse
from src.schemas import BaseModel


class ProjectBase(BaseModel):
    name: str


class ProjectResponse(ProjectBase):
    id: int
    files: list[FileResponse]
    # TODO: Add messages
