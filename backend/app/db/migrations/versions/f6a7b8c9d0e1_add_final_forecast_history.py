"""add FINAL forecast history, forecast runs and data-source updates

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-11-14 00:00:00.000000

Real-time quarterly forecasting (app.final): a queryable mirror of the append-only forecast history
(data/final/history/ledger.jsonl, the record of truth), every scheduled run, and every data-source update attempt.
A forecast row is unique per (model, issue quarter, target quarter, province) and is never updated by the sync.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'final_forecast_history',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('ledger_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('model_id', sa.String(), nullable=False),
        sa.Column('model_version', sa.String(), nullable=False),
        sa.Column('issue_quarter', sa.String(7), nullable=False),
        sa.Column('information_cutoff', sa.String(10), nullable=False),
        sa.Column('target_quarter', sa.String(7), nullable=False),
        sa.Column('lead', sa.Integer(), nullable=False),
        sa.Column('province', sa.String(), nullable=False),
        sa.Column('province_code', sa.String(), nullable=False),
        sa.Column('p_high', sa.Float(), nullable=False),
        sa.Column('risk_class', sa.String(4), nullable=False),
        sa.Column('share_pct', sa.Float(), nullable=False),
        sa.Column('range90_low', sa.Float(), nullable=False),
        sa.Column('range90_high', sa.Float(), nullable=False),
        sa.Column('generated_utc', sa.String(), nullable=False),
        sa.Column('data_version', sa.String(), nullable=False),
        sa.Column('issue_dir', sa.String(), nullable=False),
        sa.UniqueConstraint('model_id', 'issue_quarter', 'target_quarter', 'province', name='uq_final_forecast_key'),
    )
    op.create_index('ix_final_forecast_target', 'final_forecast_history', ['target_quarter', 'province'])
    op.create_table(
        'final_forecast_outcomes',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('ledger_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('province', sa.String(), nullable=False),
        sa.Column('reference_quarter', sa.String(7), nullable=False),
        sa.Column('observed_share_pct', sa.Float(), nullable=False),
        sa.Column('observed_class', sa.String(4), nullable=False),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('source_sha256', sa.String(64), nullable=False),
        sa.Column('authorized_by', sa.String(), nullable=False),
        sa.Column('recorded_utc', sa.String(), nullable=False),
        sa.UniqueConstraint('province', 'reference_quarter', name='uq_final_outcome_key'),
    )
    op.create_table(
        'final_forecast_runs',
        sa.Column('run_id', sa.String(), primary_key=True),
        sa.Column('started_utc', sa.String(), nullable=False),
        sa.Column('finished_utc', sa.String(), nullable=True),
        sa.Column('now_ph', sa.String(), nullable=False),
        sa.Column('current_quarter', sa.String(7), nullable=False),
        sa.Column('issue_quarter', sa.String(7), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('error', sa.Text(), nullable=True),
    )
    op.create_table(
        'final_source_updates',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('attempt_utc', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('detail', sa.Text(), nullable=True),
        sa.UniqueConstraint('source', 'attempt_utc', name='uq_final_source_attempt'),
    )


def downgrade() -> None:
    op.drop_table('final_source_updates')
    op.drop_table('final_forecast_runs')
    op.drop_table('final_forecast_outcomes')
    op.drop_index('ix_final_forecast_target', table_name='final_forecast_history')
    op.drop_table('final_forecast_history')
