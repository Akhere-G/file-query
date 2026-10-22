import os
import subprocess
import sys
from urllib.parse import urlparse

import pytest
import sqlalchemy as sa

SCRATCH = "filequery_migration_test"
INDEXES = {
    "ix_projects_user_id",
    "ix_files_project_id",
    "ix_chunks_file_id",
    "ix_messages_project_id",
    "ix_citations_chunk_id",
}


def alembic(url, *args):
    subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        env={**os.environ, "DATABASE_URL": url},
        capture_output=True,
        text=True,
        check=True,
    )


def index_names(url):
    engine = sa.create_engine(url)
    try:
        with engine.connect() as conn:
            rows = conn.execute(sa.text("select indexname from pg_indexes where schemaname='public'"))
            return {row[0] for row in rows}
    finally:
        engine.dispose()


@pytest.fixture
def scratch_url():
    parsed = urlparse(os.environ["TEST_DATABASE_URL"])
    scratch = parsed._replace(path=f"/{SCRATCH}").geturl()
    admin = sa.create_engine(parsed._replace(path="/postgres").geturl(), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(sa.text(f"DROP DATABASE IF EXISTS {SCRATCH} WITH (FORCE)"))
        conn.execute(sa.text(f"CREATE DATABASE {SCRATCH}"))
    engine = sa.create_engine(scratch)
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE EXTENSION vector"))
    engine.dispose()
    yield scratch
    with admin.connect() as conn:
        conn.execute(sa.text(f"DROP DATABASE IF EXISTS {SCRATCH} WITH (FORCE)"))
    admin.dispose()


def test_indexes_are_created_and_removed(scratch_url):
    alembic(scratch_url, "upgrade", "head")
    assert INDEXES <= index_names(scratch_url)

    alembic(scratch_url, "downgrade", "7c1e4b9a2d35")
    assert not INDEXES & index_names(scratch_url)


def test_model_indexes_exist_after_migrating(engine, scratch_url):
    from src.database import Base

    alembic(scratch_url, "upgrade", "head")
    declared = {index.name for table in Base.metadata.tables.values() for index in table.indexes}
    assert declared <= index_names(scratch_url)
