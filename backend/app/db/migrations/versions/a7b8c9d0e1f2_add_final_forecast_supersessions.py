"""add FINAL forecast supersessions (corrected re-issues)

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-11-14 12:00:00.000000

Mirror of the ledger's append-only "superseded" records (app.final.history.record_supersession): which issue replaced which,
why, who decided and the evidence. The superseded forecasts stay in final_forecast_history unchanged; a forecast is active when
its (model, issue) has no row here. One row per superseded issue; insert-only.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'final_forecast_supersessions',
        sa.Column('ledger_hash', sa.String(64), primary_key=True),
        sa.Column('model_id', sa.String(), nullable=False),
        sa.Column('issue_quarter', sa.String(7), nullable=False),
        sa.Column('superseded_by', sa.String(7), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('decided_by', sa.String(), nullable=False),
        sa.Column('evidence', sa.Text(), nullable=True),
        sa.Column('recorded_utc', sa.String(), nullable=False),
        sa.UniqueConstraint('model_id', 'issue_quarter', name='uq_final_supersession_issue'),
    )


def downgrade() -> None:
    op.drop_table('final_forecast_supersessions')
