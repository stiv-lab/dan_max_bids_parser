"""rename sources.type to kind

Revision ID: 2bfccf31f0dc
Revises: 5f2851ddc47c
Create Date: 2025-12-03 00:13:56.211492

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2bfccf31f0dc'
down_revision: Union[str, Sequence[str], None] = '5f2851ddc47c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Переименовать `type` -> `kind` и добавить `description`."""
    with op.batch_alter_table("sources") as batch_op:
        batch_op.alter_column("type", new_column_name="kind")
        batch_op.add_column(sa.Column("description", sa.Text(), nullable=True))


def downgrade() -> None:
    """Откатить изменения: удалить description и вернуть kind -> type."""
    with op.batch_alter_table("sources") as batch_op:
        batch_op.drop_column("description")
        batch_op.alter_column("kind", new_column_name="type")


