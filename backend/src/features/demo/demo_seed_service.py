import json
import logging
import secrets
import time
from dataclasses import dataclass
from pathlib import Path

from botocore.exceptions import ClientError
from sqlalchemy import delete, func, inspect, select
from sqlalchemy.orm import Session
from src.database import SessionLocal, engine
from src.features.auth import user_service
from src.features.auth.user_model import User
from src.features.chat import chat_service
from src.features.chat.message_model import Message
from src.features.files import file_service
from src.features.files.file_model import File, FileStatus, Project
from src.features.files.file_processing_service import (
    enqueue_files,
    process_files_locally,
)
from src.features.files.file_schema import ConfirmUploadRequest, FileCreate
from src.features.project import project_service
from src.settings import settings

logger = logging.getLogger("demo_seed")

EXAMPLE_DOCS_DIR = Path(__file__).resolve().parents[3] / "example-docs"
MANIFEST_PATH = EXAMPLE_DOCS_DIR / "manifest.json"
POLL_INTERVAL_SECONDS = 5
ASK_PAUSE_SECONDS = 3
ASK_MAX_RETRIES = 5
ASK_BASE_DELAY_SECONDS = 5
KEY_PREFIX = f"filequery/{settings.ENVIRONMENT}/projects/"
MIME_TYPES = {".txt": "text/plain", ".md": "text/markdown", ".csv": "text/csv"}

EXIT_OK = 0
EXIT_PARTIAL = 1
EXIT_REFUSED = 2


class SeedRefused(Exception):
    """Raised when the script must stop before changing anything."""


@dataclass
class SeedFile:
    name: str
    mime_type: str
    data: bytes


@dataclass
class SeedProject:
    name: str
    files: list[SeedFile]
    questions: list[str]


def load_manifest() -> SeedProject:
    manifest = json.loads(MANIFEST_PATH.read_text())
    files: list[SeedFile] = []

    for name in manifest["files"]:
        path = EXAMPLE_DOCS_DIR / name
        mime_type = MIME_TYPES.get(path.suffix.lower())
        if not path.is_file():
            raise SeedRefused(f"File listed in manifest does not exist: {name}")
        if mime_type is None:
            raise SeedRefused(f"Unsupported file type in manifest: {name}")
        files.append(SeedFile(name, mime_type, path.read_bytes()))

    return SeedProject(manifest["name"], files, manifest.get("starterQuestions", []))


def ensure_migrated():
    columns = [column["name"] for column in inspect(engine).get_columns("users")]
    if "is_demo" not in columns:
        raise SeedRefused("users.is_demo does not exist. Run: alembic upgrade head")


def get_or_create_demo_user(db: Session) -> User:
    demo_user = user_service.get_demo_user(db)
    if demo_user:
        return demo_user

    if user_service.get_user_by_email(db, settings.DEMO_USER_EMAIL):
        raise SeedRefused(
            f"{settings.DEMO_USER_EMAIL} belongs to a non-demo user. "
            "Change DEMO_USER_EMAIL; this script will not modify real users."
        )

    logger.info("Creating demo user %s", settings.DEMO_USER_EMAIL)
    demo_user = User(
        username="Demo User",
        email=settings.DEMO_USER_EMAIL,
        password_hash=user_service.get_password_hash(secrets.token_urlsafe(48)),
        is_demo=True,
    )
    db.add(demo_user)
    db.commit()
    return demo_user


def delete_demo_data(db: Session, s3, demo_user: User):
    """Delete every project the demo user owns, and everything inside them."""
    assert demo_user.is_demo

    storage_keys = db.scalars(
        select(File.storage_key)
        .join(Project, File.project_id == Project.id)
        .where(Project.user_id == demo_user.id)
    ).all()
    assert all(key.startswith(KEY_PREFIX) for key in storage_keys)

    for key in storage_keys:
        s3.delete_object(Bucket=settings.AWS_BUCKET_NAME, Key=key)

    db.execute(delete(Project).where(Project.user_id == demo_user.id))
    db.commit()
    logger.info("Deleted the demo user's projects and %s file(s)", len(storage_keys))


def ingest_files(
    db: Session, s3, demo_user: User, project: Project, seed_files: list[SeedFile]
):
    rows = file_service.create_files(
        db,
        demo_user.id,
        project.id,
        [
            FileCreate(name=file.name, mime_type=file.mime_type, size=len(file.data))
            for file in seed_files
        ],
    )

    for row, seed_file in zip(rows, seed_files):
        s3.put_object(
            Bucket=settings.AWS_BUCKET_NAME,
            Key=row.storage_key,
            Body=seed_file.data,
            ContentType=seed_file.mime_type,
        )

    files = file_service.confirm_uploads(
        db, demo_user.id, [ConfirmUploadRequest(id=row.id) for row in rows]
    )

    if settings.ENVIRONMENT == "production":
        enqueue_files(files, rename_project=False)
    else:
        process_files_locally(files)


def wait_for_processing(db: Session, project: Project):
    deadline = time.monotonic() + settings.DEMO_SEED_TIMEOUT_SECONDS
    while True:
        unfinished = db.scalar(
            select(func.count(File.id)).where(
                File.project_id == project.id,
                File.status.in_([FileStatus.pending, FileStatus.processing]),
            )
        )
        db.rollback()  # end the read transaction so the next poll sees fresh data

        if not unfinished:
            return
        if time.monotonic() > deadline:
            logger.warning("Timed out waiting for %s file(s)", unfinished)
            return
        logger.info("Waiting for %s file(s) to finish processing...", unfinished)
        time.sleep(POLL_INTERVAL_SECONDS)


def ask_question(db: Session, demo_user: User, project: Project, question: str):
    """Ask via the normal chat flow, backing off exponentially when Bedrock throttles."""
    for attempt in range(ASK_MAX_RETRIES + 1):
        last_message_id = db.scalar(
            select(func.coalesce(func.max(Message.id), 0)).where(
                Message.project_id == project.id
            )
        )
        try:
            return chat_service.send_user_message(
                db, demo_user.id, project.id, question
            )
        except ClientError as err:
            throttled = err.response["Error"]["Code"] == "ThrottlingException"
            if not throttled or attempt == ASK_MAX_RETRIES:
                raise

            # Drop the user message the failed attempt saved so the retry doesn't repeat it.
            db.rollback()
            db.execute(
                delete(Message).where(
                    Message.project_id == project.id, Message.id > last_message_id
                )
            )
            db.commit()

            delay = ASK_BASE_DELAY_SECONDS * 2**attempt
            logger.warning("Throttled by Bedrock. Retrying in %ss", delay)
            time.sleep(delay)


def seed(seed_project: SeedProject) -> int:
    s3 = file_service.get_s3_client()

    with SessionLocal() as db:
        demo_user = get_or_create_demo_user(db)
        delete_demo_data(db, s3, demo_user)

        project = project_service.create_project(db, demo_user.id, seed_project.name)
        db.commit()

        ingest_files(db, s3, demo_user, project, seed_project.files)
        wait_for_processing(db, project)

        # Local processing renames the project to an AI-generated name.
        project.name = seed_project.name
        db.commit()

        not_processed = db.scalars(
            select(File.name).where(
                File.project_id == project.id, File.status != FileStatus.processed
            )
        ).all()
        if not_processed:
            logger.error("FAILED: these files were not processed: %s", not_processed)
            return EXIT_PARTIAL

        for i, question in enumerate(seed_project.questions):
            if i > 0:
                time.sleep(ASK_PAUSE_SECONDS)
            logger.info("Asking: %s", question)
            ask_question(db, demo_user, project, question)

    return EXIT_OK


def run(apply: bool) -> int:
    try:
        seed_project = load_manifest()
        ensure_migrated()
        logger.info(
            "Target: db=%s bucket=%s environment=%s",
            engine.url.render_as_string(hide_password=True),
            settings.AWS_BUCKET_NAME,
            settings.ENVIRONMENT,
        )
        if not apply:
            logger.info("Nothing was changed. Re-run with --apply to rebuild the demo.")
            return EXIT_OK

        return seed(seed_project)
    except SeedRefused as err:
        logger.error("Refusing to run: %s", err)
        return EXIT_REFUSED
