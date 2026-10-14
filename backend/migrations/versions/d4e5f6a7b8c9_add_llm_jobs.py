"""add llm_jobs queue table

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-10-14
"""
from alembic import op
import sqlalchemy as sa

revision: str = 'd4e5f6a7b8c9'
down_revision: str = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'llm_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('kind', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('result', sa.Text(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_llm_jobs_user_id'), 'llm_jobs', ['user_id'], unique=False)
    op.create_index(op.f('ix_llm_jobs_kind'), 'llm_jobs', ['kind'], unique=False)
    op.create_index(op.f('ix_llm_jobs_status'), 'llm_jobs', ['status'], unique=False)
    op.create_index(op.f('ix_llm_jobs_created_at'), 'llm_jobs', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_llm_jobs_created_at'), table_name='llm_jobs')
    op.drop_index(op.f('ix_llm_jobs_status'), table_name='llm_jobs')
    op.drop_index(op.f('ix_llm_jobs_kind'), table_name='llm_jobs')
    op.drop_index(op.f('ix_llm_jobs_user_id'), table_name='llm_jobs')
    op.drop_table('llm_jobs')
