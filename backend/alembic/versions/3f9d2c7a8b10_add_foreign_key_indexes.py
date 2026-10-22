"""add indexes on foreign key columns

Postgres does not index foreign keys. Without these, every project, file and message
lookup (and every cascading delete) scans the whole table.

Revision ID: 3f9d2c7a8b10
Revises: 7c1e4b9a2d35
Create Date: 2026-10-22 16:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3f9d2c7a8b10"
down_revision: Union[str, Sequence[str], None] = "7c1e4b9a2d35"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INDEXES = [
    ("ix_projects_user_id", "projects", "user_id"),
    ("ix_files_project_id", "files", "project_id"),
    ("ix_chunks_file_id", "chunks", "file_id"),
    ("ix_messages_project_id", "messages", "project_id"),
    ("ix_citations_chunk_id", "citations", "chunk_id"),
]


def upgrade() -> None:
    # CONCURRENTLY avoids blocking writes on a live database; it cannot run in a transaction.
    with op.get_context().autocommit_block():
        for name, table, column in INDEXES:
            op.create_index(
                name,
                table,
                [column],
                postgresql_concurrently=True,
                if_not_exists=True,
            )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        for name, table, _ in reversed(INDEXES):
            op.drop_index(
                name,
                table_name=table,
                postgresql_concurrently=True,
                if_exists=True,
            )
