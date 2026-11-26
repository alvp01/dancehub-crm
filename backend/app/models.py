from __future__ import annotations

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint, text
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
