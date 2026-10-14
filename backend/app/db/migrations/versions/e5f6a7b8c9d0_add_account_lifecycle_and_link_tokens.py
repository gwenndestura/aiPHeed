"""add account lifecycle, demo flag and link tokens

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-10-14 15:00:00.000000

ACCT-1: self-service sign-up with email verification and admin approval,
forgot/reset password, and a view-only demo account.

Every account that exists before this migration becomes verified and
approved, so nobody is locked out: active accounts stay "active", accounts
already switched off become "deactivated".
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('admin_users', sa.Column('status', sa.String(), nullable=False, server_default='active'))
    op.add_column('admin_users', sa.Column('office_unit', sa.String(), nullable=True))
    op.add_column('admin_users', sa.Column('email_verified_at', sa.DateTime(), nullable=True))
    op.add_column('admin_users', sa.Column('approved_at', sa.DateTime(), nullable=True))
    op.add_column('admin_users', sa.Column('approved_by_id', sa.Integer(), nullable=True))
    op.add_column('admin_users', sa.Column('is_demo', sa.Boolean(), nullable=False, server_default='0'))

    # Existing accounts: verified and approved as of now.
    op.execute(
        "UPDATE admin_users SET "
        "email_verified_at = CURRENT_TIMESTAMP, "
        "approved_at = CURRENT_TIMESTAMP, "
        "status = CASE WHEN is_active THEN 'active' ELSE 'deactivated' END"
    )

    op.create_table('account_tokens',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('purpose', sa.String(), nullable=False),
    sa.Column('token_hash', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('used_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['admin_users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_account_tokens_token_hash'), 'account_tokens', ['token_hash'], unique=True)
    op.create_index(op.f('ix_account_tokens_user_id'), 'account_tokens', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_account_tokens_user_id'), table_name='account_tokens')
    op.drop_index(op.f('ix_account_tokens_token_hash'), table_name='account_tokens')
    op.drop_table('account_tokens')
    # SQLite cannot drop a column in place; batch mode rebuilds the table.
    with op.batch_alter_table('admin_users') as batch:
        batch.drop_column('is_demo')
        batch.drop_column('approved_by_id')
        batch.drop_column('approved_at')
        batch.drop_column('email_verified_at')
        batch.drop_column('office_unit')
        batch.drop_column('status')
