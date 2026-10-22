"""Test setup.

Tests need a throwaway Postgres with the pgvector extension. Point TEST_DATABASE_URL at it
(for example postgresql://test@localhost:54329/filequery_test). The URL must be on localhost and
the database name must end in `_test`, so a real .env DATABASE_URL can never be used by accident.
"""

import os
from urllib.parse import urlparse

import pytest

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

if TEST_DATABASE_URL:
    parsed = urlparse(TEST_DATABASE_URL)
    if parsed.hostname not in {"localhost", "127.0.0.1"} or not parsed.path.endswith(
        "_test"
    ):
        raise RuntimeError(
            "TEST_DATABASE_URL must point at localhost and a database ending in _test"
        )

# Real environment variables win over the backend/.env file, so these keep tests isolated.
os.environ.update(
    {
        "DATABASE_URL": TEST_DATABASE_URL or "postgresql://test@localhost:1/none_test",
        "AWS_REGION": "eu-north-1",
        "AWS_BUCKET_NAME": "test-bucket",
        "AWS_ACCESS_KEY_ID": "",
        "AWS_SECRET_ACCESS_KEY": "",
        "SQS_QUEUE_URL": "https://sqs.test/queue",
        "BEDROCK_CHAT_MODEL_ID": "test-model",
        "SECRET_KEY": "test-secret-key-test-secret-key-test-secret",
        "ALGORITHM": "HS256",
        "REDIS_URI": "memory://",
        "ENVIRONMENT": "test",
        "FRONTEND_URL": "http://localhost:3000",
        "POSTHOG_API_KEY": "",
        "POSTHOG_ID_SALT": "",
        "INTERNAL_API_SECRET": "test-internal-secret",
    }
)


def pytest_collection_modifyitems(config, items):
    if TEST_DATABASE_URL:
        return
    skip = pytest.mark.skip(reason="TEST_DATABASE_URL is not set")
    for item in items:
        if "db" in item.fixturenames or "client" in item.fixturenames:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def engine():
    from sqlalchemy import text

    from src.database import Base, engine
    from src.main import register_models

    register_models()
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def clean_state(request):
    """Empty every table and reset rate limits before each DB test."""
    if "db" not in request.fixturenames and "client" not in request.fixturenames:
        yield
        return

    from sqlalchemy import text

    from src.database import Base
    from src.limiter import limiter

    eng = request.getfixturevalue("engine")
    names = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    with eng.begin() as conn:
        conn.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))
    limiter.reset()
    yield


@pytest.fixture
def db(engine):
    from src.database import SessionLocal

    with SessionLocal() as session:
        yield session


@pytest.fixture
def aws_fakes(monkeypatch):
    from tests.fakes import install_fakes

    return install_fakes(monkeypatch)


@pytest.fixture
def client(engine, aws_fakes):
    from fastapi.testclient import TestClient

    from src.main import app

    with TestClient(app) as test_client:
        yield test_client


PASSWORD = "Passw0rdTest"


@pytest.fixture
def make_user(client):
    """Register a user through the API and return (user_json, auth_headers)."""
    counter = {"n": 0}

    def _make(email: str | None = None):
        counter["n"] += 1
        email = email or f"user{counter['n']}@example.com"
        res = client.post(
            "/api/auth/register",
            json={"username": "Test", "email": email, "password": PASSWORD},
        )
        assert res.status_code == 201, res.text
        headers = {"Authorization": f"Bearer {res.json()['access_token']}"}
        me = client.get("/api/auth/me", headers=headers).json()
        return me, headers

    return _make
