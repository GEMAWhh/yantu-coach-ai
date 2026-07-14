"""file storage backup

Revision ID: 0002_file_storage_backup
Revises: 0001_database_foundation
Create Date: 2026-07-14 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_file_storage_backup"
down_revision: str | None = "0001_database_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=40), nullable=False, server_default="inbox"),
        sa.Column("reference_count", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_assets_sha256", "assets", ["sha256"], unique=True)
    op.create_index("ix_assets_storage_path", "assets", ["storage_path"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_assets_storage_path", table_name="assets")
    op.drop_index("ix_assets_sha256", table_name="assets")
    op.drop_table("assets")
