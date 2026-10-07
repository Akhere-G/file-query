"""add full text search index to chunks

Revision ID: 2a69ffaa1032
Revises: aaf0d3f3613c
Create Date: 2026-10-07 10:28:24.106609

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2a69ffaa1032"
down_revision: Union[str, Sequence[str], None] = "aaf0d3f3613c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX ix_chunks_content_fts
        ON chunks
        USING GIN (to_tsvector('english', content))
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX ix_chunks_content_fts")
