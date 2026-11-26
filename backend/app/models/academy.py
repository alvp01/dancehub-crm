from sqlalchemy import Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Academy(Base):
    __tablename__ = "academies"
    __table_args__ = (
        UniqueConstraint("phone", name="uq_academies_phone"),
        Index("uq_academies_name_lower", text("lower(name)"), unique=True),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    administrators: Mapped[list["Administrator"]] = relationship(
        back_populates="academy"
    )
