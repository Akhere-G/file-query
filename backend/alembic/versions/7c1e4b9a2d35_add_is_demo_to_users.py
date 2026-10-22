"""add is_demo to users

Revision ID: 7c1e4b9a2d35
Revises: 554fd22cf31d
Create Date: 2026-10-21 15:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7c1e4b9a2d35"
down_revision: Union[str, Sequence[str], None] = "554fd22cf31d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column(
            "is_demo", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
    )
    op.create_index(
        "uq_users_single_demo",
        "users",
        ["is_demo"],
        unique=True,
        postgresql_where=sa.text("is_demo"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "uq_users_single_demo",
        table_name="users",
        postgresql_where=sa.text("is_demo"),
    )
    op.drop_column("users", "is_demo")
