"""add surrogate pk to link tables

Migration ID: e10bb6a39187
Previous: 68760cdd30c1
Created: 2025-12-29 23:02:44.688816

Adds surrogate primary keys to junction tables for Mathesar Extend compatibility.
Also creates a view for users with their attending/owned events.
"""

from alembic import op
import sqlalchemy as sa


revision = 'e10bb6a39187'
down_revision = '68760cdd30c1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # event_attendees: add surrogate PK
    op.add_column('event_attendees', sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False))
    op.drop_constraint('event_attendees_pkey', 'event_attendees', type_='primary')
    op.create_primary_key('event_attendees_pkey', 'event_attendees', ['id'])
    op.create_unique_constraint('event_attendees_event_id_user_id_key', 'event_attendees', ['event_id', 'user_id'])

    # project_collaborators: add surrogate PK
    op.add_column('project_collaborators', sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False))
    op.drop_constraint('project_collaborators_pkey', 'project_collaborators', type_='primary')
    op.create_primary_key('project_collaborators_pkey', 'project_collaborators', ['id'])
    op.create_unique_constraint('project_collaborators_project_id_user_id_key', 'project_collaborators', ['project_id', 'user_id'])

    # Optional: users_with_events view for Airtable-like display
    # See mathesar/VIEWS.md for manual setup instructions


def downgrade() -> None:
    # Drop view if it was manually created (see mathesar/VIEWS.md)
    op.execute("DROP VIEW IF EXISTS users_with_events;")

    # project_collaborators: restore composite PK
    op.drop_constraint('project_collaborators_project_id_user_id_key', 'project_collaborators', type_='unique')
    op.drop_constraint('project_collaborators_pkey', 'project_collaborators', type_='primary')
    op.create_primary_key('project_collaborators_pkey', 'project_collaborators', ['project_id', 'user_id'])
    op.drop_column('project_collaborators', 'id')

    # event_attendees: restore composite PK
    op.drop_constraint('event_attendees_event_id_user_id_key', 'event_attendees', type_='unique')
    op.drop_constraint('event_attendees_pkey', 'event_attendees', type_='primary')
    op.create_primary_key('event_attendees_pkey', 'event_attendees', ['event_id', 'user_id'])
    op.drop_column('event_attendees', 'id')
