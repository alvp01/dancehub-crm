from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Academy(Base):
    __tablename__ = "academies"
    __table_args__ = (
        UniqueConstraint("phone", name="uq_academies_phone"),
        Index("uq_academies_name_lower", text("lower(name)"), unique=True),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    administrators: Mapped[list[Administrator]] = relationship(
        back_populates="academy"
    )


class Administrator(Base):
    __tablename__ = "administrators"
    __table_args__ = (UniqueConstraint("email", name="uq_administrators_email"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    academy_id: Mapped[str] = mapped_column(
        ForeignKey("academies.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    academy: Mapped[Academy] = relationship(back_populates="administrators")


class RefreshSession(Base):
    __tablename__ = "refresh_sessions"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_refresh_sessions_token_hash"),
        Index("ix_refresh_sessions_administrator_id", "administrator_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    administrator_id: Mapped[str] = mapped_column(
        ForeignKey("administrators.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
