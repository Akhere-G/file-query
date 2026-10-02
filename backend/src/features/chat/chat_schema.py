from src.schemas import BaseModel


class MessageBase(BaseModel):
    content: str


class MessageResponse(MessageBase):
    id: str
    project_id: int
    owner: str
    # chunks: list["Chunk"]


class MessageCreate(MessageBase):
    pass
