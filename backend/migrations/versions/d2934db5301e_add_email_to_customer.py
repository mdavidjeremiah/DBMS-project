"""add_email_to_customer

Revision ID: d2934db5301e
Revises: 0012_workflow_accounts
Create Date: 2026-10-29 18:07:37.937615
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd2934db5301e'
down_revision: Union[str, Sequence[str], None] = '0012_workflow_accounts'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('customer', sa.Column('email', sa.String(length=255), nullable=True))


def downgrade() -> None:
    pass  # Keeps downgrade safe so it won't crash if the column isn't there