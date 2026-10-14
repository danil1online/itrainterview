"""add run_logs table

Revision ID: a1b2c3d4e5f6
Revises: 59f93e6b64cb
Create Date: 2026-10-12
"""
from alembic import op
import sqlalchemy as sa

revision: str = 'a1b2c3d4e5f6'
down_revision: str = '59f93e6b64cb'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'run_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('language', sa.String(length=16), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('passed_count', sa.Integer(), nullable=False),
        sa.Column('total_count', sa.Integer(), nullable=False),
        sa.Column('results', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'task_id')
    )
    op.create_index(op.f('ix_run_logs_task_id'), 'run_logs', ['task_id'], unique=False)
    op.create_index(op.f('ix_run_logs_user_id'), 'run_logs', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_run_logs_user_id'), table_name='run_logs')
    op.drop_index(op.f('ix_run_logs_task_id'), table_name='run_logs')
    op.drop_table('run_logs')
