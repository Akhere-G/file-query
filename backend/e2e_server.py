"""Backend for the Playwright end-to-end tests.

Runs the real FastAPI app, database schema and ingestion pipeline, but against a throwaway
Postgres database and with S3, SQS and Bedrock replaced by the in-memory fakes from
tests/fakes.py. Nothing here can reach AWS or the production database.

    ../.venv-or-venv/bin/python e2e_server.py

Environment: E2E_DATABASE_URL (default postgresql://test@localhost:5433/filequery_e2e_test),
E2E_PORT (default 8000), FRONTEND_URL (default http://localhost:3000).
"""

import os
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

BACKEND_DIR = Path(__file__).resolve().parent
DATABASE_URL = os.environ.get("E2E_DATABASE_URL", "postgresql://test@localhost:5433/filequery_e2e_test")
PORT = int(os.environ.get("E2E_PORT", "8000"))
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
PUBLIC_URL = os.environ.get("E2E_PUBLIC_URL", f"http://localhost:{PORT}")

parsed = urlparse(DATABASE_URL)
if parsed.hostname not in {"localhost", "127.0.0.1"} or not parsed.path.endswith("_test"):
    sys.exit("E2E_DATABASE_URL must point at localhost and a database ending in _test")

# Never pick up backend/.env (it points at real cloud services): run from an empty directory
# and stop python-dotenv from loading it either.
os.chdir(tempfile.mkdtemp(prefix="filequery-e2e-"))
sys.path.insert(0, str(BACKEND_DIR))

import dotenv  # noqa: E402

dotenv.load_dotenv = lambda *args, **kwargs: False

os.environ.update(
    {
        "DATABASE_URL": DATABASE_URL,
        "AWS_REGION": "eu-north-1",
        "AWS_BUCKET_NAME": "e2e-bucket",
        "AWS_ACCESS_KEY_ID": "",
        "AWS_SECRET_ACCESS_KEY": "",
        "SQS_QUEUE_URL": "https://sqs.invalid/queue",
        "BEDROCK_CHAT_MODEL_ID": "e2e-model",
        "SECRET_KEY": "e2e-secret-key-e2e-secret-key-e2e-secret-key",
        "ALGORITHM": "HS256",
        "REDIS_URI": "memory://",
        "ENVIRONMENT": "test",
        "FRONTEND_URL": FRONTEND_URL,
        "POSTHOG_API_KEY": "",
        "POSTHOG_ID_SALT": "",
        "INTERNAL_API_SECRET": os.environ.get("INTERNAL_API_SECRET", "e2e-internal-secret"),
    }
)


def recreate_database():
    import psycopg2
    from psycopg2 import sql

    name = parsed.path.lstrip("/")
    admin = psycopg2.connect(
        host=parsed.hostname, port=parsed.port, user=parsed.username, dbname="postgres"
    )
    admin.autocommit = True
    with admin.cursor() as cursor:
        cursor.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name)))
        cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    admin.close()


recreate_database()

from fastapi import File, Form, HTTPException, UploadFile  # noqa: E402
from sqlalchemy import text  # noqa: E402
from src import aws  # noqa: E402
from src.database import Base, engine  # noqa: E402
from src.features.demo import demo_service  # noqa: E402
from src.main import app, register_models  # noqa: E402
from src.settings import settings  # noqa: E402
from tests.fakes import FakeS3, Fakes  # noqa: E402

assert settings.REDIS_URI == "memory://" and settings.DATABASE_URL == DATABASE_URL

register_models()
with engine.begin() as connection:
    connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
Base.metadata.create_all(engine)


class BrowserReachableS3(FakeS3):
    """Presigned POSTs point at this server, which enforces the same conditions S3 would."""

    def __init__(self):
        super().__init__()
        self.conditions = {}

    def generate_presigned_post(self, Bucket, Key, **kwargs):
        self.conditions[Key] = kwargs.get("Conditions", [])
        return {
            "url": f"{PUBLIC_URL}/__fake_s3/upload",
            "fields": {"key": Key, **kwargs.get("Fields", {})},
        }


fakes = Fakes().use_semantic()
fakes.s3 = BrowserReachableS3()

# Real embedding takes a moment; without a delay a file would be "processed" before the UI
# ever shows the processing state, which is the behaviour the end-to-end tests want to see.
EMBED_DELAY_SECONDS = float(os.environ.get("E2E_EMBED_DELAY_SECONDS", "1.5"))
_embed = fakes.bedrock.invoke_model


def slow_embed(**kwargs):
    time.sleep(EMBED_DELAY_SECONDS)
    return _embed(**kwargs)


fakes.bedrock.invoke_model = slow_embed
aws.s3_client = lambda: fakes.s3
aws.sqs_client = lambda: fakes.sqs
aws.bedrock_runtime_client = lambda: fakes.bedrock
aws.bedrock_agent_client = lambda: fakes.agent


class InMemoryRedis:
    def __init__(self):
        self.counts = {}

    def incr(self, key):
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    def expire(self, key, seconds):
        pass


_redis = InMemoryRedis()
demo_service.get_redis = lambda: _redis


@app.post("/__fake_s3/upload", status_code=204)
async def fake_s3_upload(key: str = Form(...), file: UploadFile = File(...)):
    data = await file.read()
    for condition in fakes.s3.conditions.get(key, []):
        if isinstance(condition, list) and condition[0] == "content-length-range":
            if not condition[1] <= len(data) <= condition[2]:
                raise HTTPException(status_code=403, detail="EntityTooLarge or EntityTooSmall")
    fakes.s3.put(key, data)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
