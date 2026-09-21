"""Create the initial Hardware World schema.

This baseline uses the existing SQLAlchemy metadata because the repository did
not contain a prior migration history. Future schema changes must be normal,
reviewed Alembic operations rather than metadata.create_all().
"""
from alembic import op
import models

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    models.Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    raise RuntimeError("The initial schema is destructive to downgrade; reset the local database intentionally instead.")
