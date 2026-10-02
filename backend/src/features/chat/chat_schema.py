from datetime import datetime

from src.schemas import BaseModel


class MessageBase(BaseModel):
    content: str


class MessageResponse(MessageBase):
    id: int
    project_id: int
    owner: str
    created_at: datetime
    # chunks: list["Chunk"]


class MessageCreate(MessageBase):
    pass
