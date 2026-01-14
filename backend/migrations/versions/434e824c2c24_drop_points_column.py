"""drop points column

Migration ID: 434e824c2c24
Previous: e10bb6a39187
Created: 2026-01-13

Drops the points column from projects table.
Points is now a computed_field from len(votes).

For legacy projects with points > vote count, creates votes from event attendees
to preserve accurate point counts. These are old events where manual scoring
predated the voting system.
"""

from alembic import op
import sqlalchemy as sa


revision = '434e824c2c24'
down_revision = 'e10bb6a39187'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Create votes for legacy projects where points > actual vote count.
    # Uses event attendees as voters (excluding project owner).
    # Row numbering ensures we create exactly (points - current_votes) new votes.
    conn.execute(sa.text("""
        INSERT INTO votes (id, voter_id, project_id, event_id)
        SELECT gen_random_uuid(), numbered.user_id, numbered.project_id, numbered.event_id
        FROM (
            SELECT 
                p.id as project_id,
                p.event_id,
                ea.user_id,
                p.points - COALESCE(vc.vote_count, 0) as votes_needed,
                ROW_NUMBER() OVER (PARTITION BY p.id ORDER BY ea.user_id) as rn
            FROM projects p
            JOIN event_attendees ea ON ea.event_id = p.event_id
            LEFT JOIN project_collaborators pc ON pc.project_id = p.id AND pc.user_id = ea.user_id
            LEFT JOIN (
                SELECT project_id, COUNT(*) as vote_count FROM votes GROUP BY project_id
            ) vc ON vc.project_id = p.id
            LEFT JOIN votes existing ON existing.project_id = p.id AND existing.voter_id = ea.user_id
            WHERE p.points > COALESCE(vc.vote_count, 0)
              AND ea.user_id != p.owner_id
              AND pc.user_id IS NULL
              AND existing.id IS NULL
        ) numbered
        WHERE numbered.rn <= numbered.votes_needed
    """))

    op.drop_index('ix_projects_points', table_name='projects', if_exists=True)
    op.drop_column('projects', 'points')


def downgrade() -> None:
    op.add_column('projects', sa.Column('points', sa.Integer(), nullable=False, server_default='0'))
    op.create_index('ix_projects_points', 'projects', ['points'])

    # Restore points from vote counts
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE projects p
        SET points = (
            SELECT COUNT(*)
            FROM votes v
            WHERE v.project_id = p.id
        )
    """))
