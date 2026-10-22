from datetime import datetime

from pydantic import Field, field_validator, model_validator
from src.features.files.file_schema import ChunkResponse
from src.schemas import BaseModel
from src.settings import settings


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
    content: str = Field(min_length=1, max_length=settings.MAX_MESSAGE_LENGTH)

    @field_validator("content", mode="before")
    @classmethod
    def strip_content(cls, value):
        return value.strip() if isinstance(value, str) else value


class PaginatedMessages(BaseModel):
    messages: list[MessageResponse]
    has_more: bool
    next_cursor: int | None
