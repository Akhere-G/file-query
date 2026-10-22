"""store user emails in lower case

Emails were matched case-sensitively, so A@x.com and a@x.com could be two accounts.
The application now lower-cases emails; this migration converts existing rows and adds
a constraint so the database enforces it.

Revision ID: 9b4e6a1c5d27
Revises: 3f9d2c7a8b10
Create Date: 2026-10-22 17:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9b4e6a1c5d27"
down_revision: Union[str, Sequence[str], None] = "3f9d2c7a8b10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    collisions = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT count(*) FROM (SELECT lower(email) FROM users "
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
    op.create_check_constraint(
        "ck_users_email_lowercase", "users", sa.text("email = lower(email)")
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_email_lowercase", "users", type_="check")
