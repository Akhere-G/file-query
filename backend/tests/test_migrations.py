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
        conn.execute(sa.text(f"DROP DATABASE IF EXISTS {SCRATCH} WITH (FORCE)"))
        conn.execute(sa.text(f"CREATE DATABASE {SCRATCH}"))
    scratch = sa.create_engine(scratch_url)
    with scratch.begin() as conn:
        conn.execute(sa.text("CREATE EXTENSION vector"))
    scratch.dispose()
    yield scratch_url
    with admin.connect() as conn:
        conn.execute(sa.text(f"DROP DATABASE IF EXISTS {SCRATCH} WITH (FORCE)"))
    admin.dispose()


def test_upgrade_adds_indexes_and_downgrade_removes_them(scratch_url):
    alembic(scratch_url, "upgrade", "head")
    assert EXPECTED <= index_names(scratch_url)

    alembic(scratch_url, "downgrade", "7c1e4b9a2d35")
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


def psql(url, sql):
    engine = sa.create_engine(url)
    try:
        with engine.begin() as conn:
            conn.execute(sa.text(sql))
    finally:
        engine.dispose()


def emails(url):
    engine = sa.create_engine(url)
    with engine.connect() as conn:
        rows = [r[0] for r in conn.execute(sa.text("select email from users order by id"))]
    engine.dispose()
    return rows


INSERT = (
    "insert into users (username, email, password_hash, created_at, updated_at) "
    "values ('t', '{email}', 'x', now(), now())"
)


def test_email_migration_lowercases_existing_rows(scratch_url):
    alembic(scratch_url, "upgrade", "3f9d2c7a8b10")
    psql(scratch_url, INSERT.format(email="Mixed@Example.com"))

    alembic(scratch_url, "upgrade", "head")
    assert emails(scratch_url) == ["mixed@example.com"]

    with pytest.raises(sa.exc.IntegrityError):
        psql(scratch_url, INSERT.format(email="Upper@Example.com"))


def test_email_migration_refuses_to_merge_accounts(scratch_url):
    alembic(scratch_url, "upgrade", "3f9d2c7a8b10")
    psql(scratch_url, INSERT.format(email="dup@example.com"))
    psql(scratch_url, INSERT.format(email="DUP@example.com"))

    with pytest.raises(subprocess.CalledProcessError) as failed:
        alembic(scratch_url, "upgrade", "head")
    assert "different letter casing" in failed.value.stderr
    assert sorted(emails(scratch_url)) == ["DUP@example.com", "dup@example.com"]
