import enum
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base


class FileStatus(enum.Enum):
    pending = "pending"
    processing = "processing"
    processed = "processed"
    error = "error"


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE")
    )
    user: Mapped["User"] = relationship(back_populates="projects")  # type: ignore  # noqa: F821
    files: Mapped[list["File"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="File.created_at",
        passive_deletes=True,
    )
    messages: Mapped[list["Message"]] = relationship(  # noqa: F821 # type: ignore
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
        passive_deletes=True,
    )


class File(Base):
    __tablename__ = "files"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(255))
    size: Mapped[int] = mapped_column(Integer)
    status: Mapped[FileStatus] = mapped_column(
        Enum(FileStatus), default=FileStatus.pending
    )
    storage_key: Mapped[str] = mapped_column(
        String(255), unique=True, default=lambda: str(uuid4())
    )
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE")
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    project: Mapped["Project"] = relationship(back_populates="files")
    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="file",
        cascade="all, delete-orphan",
        order_by="Chunk.created_at",
        passive_deletes=True,
    )


class Chunk(Base):
    __tablename__ = "chunks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id", ondelete="CASCADE"))
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024), nullable=True)
    file: Mapped["File"] = relationship(back_populates="chunks")
    messages: Mapped[list["Message"]] = relationship(  # noqa: F821 # type: ignore
        back_populates="chunk",
        order_by="Message.created_at",
        passive_deletes=True,
    )
