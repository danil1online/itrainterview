"""add vibe_tasks and vibe_sessions tables

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-10-13
"""
from alembic import op
import sqlalchemy as sa

revision: str = 'c3d4e5f6a7b8'
down_revision: str = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'vibe_tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('slug', sa.String(length=96), nullable=False),
        sa.Column('task_type', sa.String(length=16), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description_md', sa.Text(), nullable=False),
        sa.Column('initial_code', sa.Text(), nullable=False),
        sa.Column('hidden_tests', sa.JSON(), nullable=False),
        sa.Column('reference_solution', sa.Text(), nullable=False),
        sa.Column('mutants', sa.JSON(), nullable=False),
        sa.Column('min_mutants_caught', sa.Integer(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_vibe_tasks_slug'), 'vibe_tasks', ['slug'], unique=True)
    op.create_table(
        'vibe_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('messages', sa.JSON(), nullable=False),
        sa.Column('code', sa.Text(), nullable=False),
        sa.Column('prompts_count', sa.Integer(), nullable=False),
        sa.Column('run_count', sa.Integer(), nullable=False),
        sa.Column('last_run', sa.JSON(), nullable=False),
        sa.Column('score', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['vibe_tasks.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'task_id', name='uq_vibe_session_user_task')
    )
    op.create_index(op.f('ix_vibe_sessions_task_id'), 'vibe_sessions', ['task_id'], unique=False)
    op.create_index(op.f('ix_vibe_sessions_user_id'), 'vibe_sessions', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_vibe_sessions_user_id'), table_name='vibe_sessions')
    op.drop_index(op.f('ix_vibe_sessions_task_id'), table_name='vibe_sessions')
    op.drop_table('vibe_sessions')
    op.drop_index(op.f('ix_vibe_tasks_slug'), table_name='vibe_tasks')
    op.drop_table('vibe_tasks')
