import os
from urllib.parse import urlparse

import pytest

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

if not TEST_DATABASE_URL:
    pytest.exit("Set TEST_DATABASE_URL to a local Postgres database ending in _test")

parsed = urlparse(TEST_DATABASE_URL)
if parsed.hostname not in {"localhost", "127.0.0.1"} or not parsed.path.endswith("_test"):
    pytest.exit("TEST_DATABASE_URL must point at localhost and a database ending in _test")

os.environ.update(
    {
        "DATABASE_URL": TEST_DATABASE_URL,
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
    }
)

PASSWORD = "Passw0rdTest"


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
    if "db" not in request.fixturenames and "client" not in request.fixturenames:
        yield
        return

    from sqlalchemy import text

    from src.database import Base

    with request.getfixturevalue("engine").begin() as conn:
        names = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
        conn.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))
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


class FakeRedis:
    def __init__(self):
        self.counts = {}

    def incr(self, key):
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    def expire(self, key, seconds):
        pass


@pytest.fixture
def client(engine, aws_fakes, monkeypatch):
    from fastapi.testclient import TestClient

    from src.features.demo import demo_service
    from src.main import app

    fake_redis = FakeRedis()
    monkeypatch.setattr(demo_service, "get_redis", lambda: fake_redis)

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
def make_user(client):
    counter = {"n": 0}

    def make(email: str | None = None):
        counter["n"] += 1
        email = email or f"user{counter['n']}@example.com"
        res = client.post(
            "/api/auth/register",
            json={"username": "Test", "email": email, "password": PASSWORD},
        )
        assert res.status_code == 201, res.text
        headers = {"Authorization": f"Bearer {res.json()['access_token']}"}
        return client.get("/api/auth/me", headers=headers).json(), headers

    return make
