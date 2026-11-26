"""Create academy and administrator tables."""

from alembic import op
import sqlalchemy as sa

revision = "0002_registration"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "academies",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.UniqueConstraint("phone", name="uq_academies_phone"),
    )
    op.create_index(
        "uq_academies_name_lower",
        "academies",
        [sa.text("lower(name)")],
        unique=True,
    )
    op.create_table(
        "administrators",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("academy_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=128), nullable=False),
        sa.ForeignKeyConstraint(
            ["academy_id"], ["academies.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("email", name="uq_administrators_email"),
    )


def downgrade() -> None:
    op.drop_table("administrators")
    op.drop_table("academies")
