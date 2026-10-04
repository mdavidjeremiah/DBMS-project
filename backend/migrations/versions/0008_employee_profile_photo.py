"""Store employee profile photo filenames.

Revision ID: 0008_profile_photo
Revises: 0007_password_lifecycle
"""
from alembic import op
import sqlalchemy as sa


revision = "0008_profile_photo"
down_revision = "0007_password_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("employee")}
    if "profile_photo_filename" not in columns:
        op.add_column(
            "employee",
            sa.Column("profile_photo_filename", sa.String(length=255), nullable=True),
        )


def downgrade() -> None:
    raise RuntimeError("Employee profile photo metadata must not be removed by downgrading.")
