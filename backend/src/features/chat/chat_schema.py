from datetime import datetime

from pydantic import Field, model_validator
from src.features.files.file_schema import ChunkResponse
from src.schemas import BaseModel


class MessageBase(BaseModel):
    content: str


class MessageResponse(MessageBase):
    id: int
    project_id: int
    owner: str
    created_at: datetime
    citations: list[ChunkResponse] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def flatten_citations(cls, data):
        if isinstance(data, dict):
            if "chunks" in data:
                data["citations"] = data["chunks"]
        elif hasattr(data, "chunks"):
            return {
                "id": data.id,
                "project_id": data.project_id,
                "owner": data.owner,
                "created_at": data.created_at,
                "citations": data.chunks,
                "content": data.content,
            }

        return data


class MessageCreate(MessageBase):
    pass


class PaginatedMessages(BaseModel):
    messages: list[MessageResponse]
    has_more: bool
    next_cursor: int | None
