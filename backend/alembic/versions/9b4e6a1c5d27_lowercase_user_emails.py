"""store user emails in lower case

Revision ID: 9b4e6a1c5d27
Revises: 3f9d2c7a8b10
Create Date: 2026-10-22 17:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "9b4e6a1c5d27"
down_revision: Union[str, Sequence[str], None] = "3f9d2c7a8b10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    collisions = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT count(*) FROM (SELECT 1 FROM users "
                "GROUP BY lower(email) HAVING count(*) > 1) AS duplicated"
            )
        )
        .scalar_one()
    )
    if collisions:
        raise RuntimeError(
            f"{collisions} email address(es) exist with different letter casing. Merge or "
            "remove those accounts first: SELECT lower(email), count(*) FROM users "
            "GROUP BY 1 HAVING count(*) > 1"
        )

    op.execute("UPDATE users SET email = lower(email) WHERE email <> lower(email)")


def downgrade() -> None:
    pass
