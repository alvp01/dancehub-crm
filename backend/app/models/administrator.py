from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


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
    academy: Mapped["Academy"] = relationship(back_populates="administrators")
    refresh_sessions: Mapped[list["RefreshSession"]] = relationship(
        back_populates="administrator"
    )
