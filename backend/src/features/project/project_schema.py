from src.schemas import BaseModel


class ProjectBase(BaseModel):
    name: str


class RenameProjectRequest(BaseModel):
    name: str


class ProjectSummary(ProjectBase):
    id: int
