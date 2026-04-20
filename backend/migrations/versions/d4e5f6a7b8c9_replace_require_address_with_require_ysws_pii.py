"""replace require_address with require_ysws_pii

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-19

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("events", sa.Column("require_ysws_pii", sa.Boolean(), nullable=False, server_default="false"))
    op.drop_column("events", "require_address")


def downgrade() -> None:
    op.add_column("events", sa.Column("require_address", sa.Boolean(), nullable=False, server_default="false"))
    op.drop_column("events", "require_ysws_pii")
