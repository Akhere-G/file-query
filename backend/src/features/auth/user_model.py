from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base
from src.features.files.file_model import Project


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(2555), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    projects: Mapped["Project"] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="Project.created_at",
        passive_deletes=True,
    )
