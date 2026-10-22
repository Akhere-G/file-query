from datetime import datetime
from typing import Annotated

from pydantic import Field, StringConstraints, model_validator
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
    content: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
    ]


class PaginatedMessages(BaseModel):
    messages: list[MessageResponse]
    has_more: bool
    next_cursor: int | None
