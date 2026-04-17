"""Add validation system fields and superadmin flag.

Events: drop ysws_checks_enabled, add repo_validation, demo_validation,
        custom_validator, deleted_at.
Projects: add validation_status, validation_message.
Users: add is_superadmin.
"""

from alembic import op
import sqlalchemy as sa

revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── events ──────────────────────────────────────────────────────────────
    op.drop_column('events', 'ysws_checks_enabled')

    op.add_column('events', sa.Column('repo_validation', sa.String(length=20), nullable=False, server_default='github'))
    op.add_column('events', sa.Column('demo_validation', sa.String(length=20), nullable=False, server_default='none'))
    op.add_column('events', sa.Column('custom_validator', sa.String(length=50), nullable=True))
    op.add_column('events', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))

    # ── projects ─────────────────────────────────────────────────────────────
    op.add_column('projects', sa.Column('validation_status', sa.String(length=20), nullable=False, server_default='pending'))
    op.add_column('projects', sa.Column('validation_message', sa.Text(), nullable=False, server_default=''))

    # ── users ─────────────────────────────────────────────────────────────────
    op.add_column('users', sa.Column('is_superadmin', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    op.drop_column('users', 'is_superadmin')

    op.drop_column('projects', 'validation_message')
    op.drop_column('projects', 'validation_status')

    op.drop_column('events', 'deleted_at')
    op.drop_column('events', 'custom_validator')
    op.drop_column('events', 'demo_validation')
    op.drop_column('events', 'repo_validation')

    op.add_column('events', sa.Column('ysws_checks_enabled', sa.Boolean(), nullable=False, server_default='false'))
