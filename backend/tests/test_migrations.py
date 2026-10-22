"""Run the real Alembic chain on a scratch database and check the result."""

import os
import subprocess
import sys
from urllib.parse import urlparse

import pytest
import sqlalchemy as sa

TEST_URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_URL, reason="TEST_DATABASE_URL is not set")

SCRATCH = "filequery_migration_test"
EXPECTED = {
    "ix_projects_user_id",
    "ix_files_project_id",
    "ix_chunks_file_id",
    "ix_messages_project_id",
    "ix_citations_chunk_id",
}


def alembic(url, *args):
    env = {**os.environ, "DATABASE_URL": url}
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )


def index_names(url):
    engine = sa.create_engine(url)
    with engine.connect() as conn:
        rows = conn.execute(sa.text("select indexname from pg_indexes where schemaname='public'"))
        names = {row[0] for row in rows}
    engine.dispose()
    return names


@pytest.fixture
def scratch_url():
    parsed = urlparse(TEST_URL)
    admin_url = parsed._replace(path="/postgres").geturl()
    scratch_url = parsed._replace(path=f"/{SCRATCH}").geturl()
    admin = sa.create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(sa.text(f"DROP DATABASE IF EXISTS {SCRATCH}"))
        conn.execute(sa.text(f"CREATE DATABASE {SCRATCH}"))
    scratch = sa.create_engine(scratch_url)
    with scratch.begin() as conn:
        conn.execute(sa.text("CREATE EXTENSION vector"))
    scratch.dispose()
    yield scratch_url
    with admin.connect() as conn:
        conn.execute(sa.text(f"DROP DATABASE IF EXISTS {SCRATCH}"))
    admin.dispose()


def test_upgrade_adds_indexes_and_downgrade_removes_them(scratch_url):
    alembic(scratch_url, "upgrade", "head")
    assert EXPECTED <= index_names(scratch_url)

    alembic(scratch_url, "downgrade", "-1")
    assert not (EXPECTED & index_names(scratch_url))

    alembic(scratch_url, "upgrade", "head")
    assert EXPECTED <= index_names(scratch_url)


def test_every_index_declared_on_the_models_exists_after_migrating(engine, scratch_url):
    from src.database import Base

    alembic(scratch_url, "upgrade", "head")
    declared = {
        index.name for table in Base.metadata.tables.values() for index in table.indexes
    }
    assert EXPECTED <= declared
    assert declared <= index_names(scratch_url)
