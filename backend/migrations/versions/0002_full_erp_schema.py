"""Create Full ERP Schema tables.

Revision ID: 0002_full_erp_schema
Revises: 0001_initial_schema
Create Date: 2026-09-29
"""
from alembic import op
import models

revision = "0002_full_erp_schema"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    models.Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    raise RuntimeError("Downgrading full ERP schema is destructive; restore from backup instead.")
