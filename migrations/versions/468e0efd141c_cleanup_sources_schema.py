"""cleanup sources schema

Revision ID: 468e0efd141c
Revises: 2bfccf31f0dc
Create Date: 2025-12-03 00:44:04.654638

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '468e0efd141c'
down_revision: Union[str, Sequence[str], None] = '2bfccf31f0dc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    with op.batch_alter_table("sources") as batch_op:
        batch_op.drop_column("base_url")
        batch_op.drop_column("priority")


def downgrade():
    with op.batch_alter_table("sources") as batch_op:
        batch_op.add_column(sa.Column("priority", sa.Integer, nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("base_url", sa.String(length=1024), nullable=True))

