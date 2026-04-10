from datetime import datetime
from typing import List

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer


class Base(DeclarativeBase):
    pass


class UserDB(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="staff")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    sessions: Mapped[List["SessionDB"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class SessionDB(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    user: Mapped["UserDB"] = relationship(back_populates="sessions")