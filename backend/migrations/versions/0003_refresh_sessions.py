"""Create refresh session storage."""

from alembic import op
import sqlalchemy as sa

revision = "0003_refresh_sessions"
down_revision = "0002_registration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "refresh_sessions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("administrator_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["administrator_id"], ["administrators.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("token_hash", name="uq_refresh_sessions_token_hash"),
    )
    op.create_index(
        "ix_refresh_sessions_administrator_id",
        "refresh_sessions",
        ["administrator_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_refresh_sessions_administrator_id", table_name="refresh_sessions"
    )
    op.drop_table("refresh_sessions")
