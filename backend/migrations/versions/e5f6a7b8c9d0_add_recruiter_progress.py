"""add recruiter_progress table (mandatory technical questions)

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-10-18
"""
from alembic import op
import sqlalchemy as sa

revision: str = 'e5f6a7b8c9d0'
down_revision: str = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'recruiter_progress',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('task_question', sa.Text(), nullable=True),
        sa.Column('tech_question', sa.Text(), nullable=True),
        sa.Column('meta', sa.JSON(), nullable=False),
        sa.Column('task_asked', sa.Boolean(), nullable=False),
        sa.Column('tech_asked', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_recruiter_progress_user_id'), 'recruiter_progress', ['user_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_recruiter_progress_user_id'), table_name='recruiter_progress')
    op.drop_table('recruiter_progress')
