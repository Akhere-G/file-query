from sqlalchemy import Boolean, CheckConstraint, Index, Integer, String, false, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base
from src.features.files.file_model import Project


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("email = lower(email)", name="ck_users_email_lowercase"),
        Index(
            "uq_users_single_demo",
            "is_demo",
            unique=True,
            postgresql_where=text("is_demo"),
        ),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(2555), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    is_demo: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false()
    )
    projects: Mapped[list["Project"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="Project.created_at",
        passive_deletes=True,
    )
