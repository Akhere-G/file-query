from src.schemas import BaseModel


class ProjectBase(BaseModel):
    name: str


class RenameProjectRequest(BaseModel):
    name: str


class ProjectSummary(ProjectBase):
    """Projects are listed without their files and messages; those have their own endpoints."""

    id: int
