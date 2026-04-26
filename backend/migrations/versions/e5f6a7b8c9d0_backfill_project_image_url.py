"""backfill project image_url with placeholder for empty rows

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-04-26

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PLACEHOLDER = "https://cdn.hackclub.com/019dca36-2c32-7627-9db0-e574d55fba28/image.png"


def upgrade() -> None:
    op.execute(
        sa.text("UPDATE projects SET image_url = :url WHERE image_url = ''").bindparams(url=PLACEHOLDER)
    )


def downgrade() -> None:
    op.execute(
        sa.text("UPDATE projects SET image_url = '' WHERE image_url = :url").bindparams(url=PLACEHOLDER)
    )
