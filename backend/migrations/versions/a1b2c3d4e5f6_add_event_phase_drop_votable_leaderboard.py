"""add_event_phase_drop_votable_leaderboard

Migration ID: a1b2c3d4e5f6
Previous: 28f961df26a5

Replaces the votable and leaderboard_enabled boolean columns with a single
phase string column (draft/submission/voting/closed). Data is migrated:
  - leaderboard_enabled=True  → phase='closed'   (closed implies voting also happened)
  - votable=True              → phase='voting'
  - otherwise                 → phase='submission'
"""

from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f6'
down_revision = '28f961df26a5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add phase column with a safe default, then backfill from old booleans
    op.add_column('events', sa.Column('phase', sa.String(length=20), nullable=False, server_default='submission'))

    # Migrate existing data: closed > voting > submission (in priority order)
    op.execute("UPDATE events SET phase = 'closed'     WHERE leaderboard_enabled = TRUE")
    op.execute("UPDATE events SET phase = 'voting'     WHERE leaderboard_enabled = FALSE AND votable = TRUE")
    # Remaining rows already have the 'submission' default from server_default

    op.drop_column('events', 'votable')
    op.drop_column('events', 'leaderboard_enabled')


def downgrade() -> None:
    op.add_column('events', sa.Column('votable', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('events', sa.Column('leaderboard_enabled', sa.Boolean(), nullable=False, server_default='false'))

    op.execute("UPDATE events SET votable = TRUE            WHERE phase IN ('voting', 'closed')")
    op.execute("UPDATE events SET leaderboard_enabled = TRUE WHERE phase = 'closed'")

    op.drop_column('events', 'phase')
