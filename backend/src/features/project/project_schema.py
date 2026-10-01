from src.schemas import BaseModel


class ProjectBase(BaseModel):
    name: str


class ProjectResponse(ProjectBase):
    id: int
