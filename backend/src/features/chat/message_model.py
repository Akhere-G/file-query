import enum

from sqlalchemy import Enum, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base
from src.features.files.file_model import Chunk, Project


class MessageOwner(enum.Enum):
    user = "user"
    assistant = "assistant"


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    content: Mapped[str] = mapped_column(Text)
    owner: Mapped[MessageOwner] = mapped_column(Enum(MessageOwner))
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE")
    )
    reference_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("chunks.id", ondelete="SET NULL"), nullable=True
    )
    project: Mapped["Project"] = relationship(back_populates="messages")
    chunk: Mapped["Chunk | None"] = relationship(back_populates="messages")
