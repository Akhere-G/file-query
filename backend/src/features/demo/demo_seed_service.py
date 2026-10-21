import hashlib
import json
import logging
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from botocore.exceptions import ClientError
from sqlalchemy import delete, func, inspect, select, text
from sqlalchemy.orm import Session
from src.database import SessionLocal, engine
from src.features.auth import user_service
from src.features.auth.user_model import User
from src.features.chat import chat_service
from src.features.chat.message_model import Message
from src.features.files import file_service
from src.features.files.file_model import Chunk, File, FileStatus, Project
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
ADVISORY_LOCK_KEY = 726_041_907
POLL_INTERVAL_SECONDS = 5
KEY_PREFIX = f"filequery/{settings.ENVIRONMENT}/projects/"

MIME_TYPES = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".csv": "text/csv",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
}

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
    sha256: str


@dataclass
class SeedProject:
    name: str
    files: list[SeedFile]
    questions: list[str]


def load_manifest() -> list[SeedProject]:
    if not MANIFEST_PATH.exists():
        raise SeedRefused(f"Manifest not found: {MANIFEST_PATH}")

    manifest = json.loads(MANIFEST_PATH.read_text())
    projects: list[SeedProject] = []

    for project in manifest["projects"]:
        files: list[SeedFile] = []
        for name in project["files"]:
            path = EXAMPLE_DOCS_DIR / name
            mime_type = MIME_TYPES.get(path.suffix.lower())
            if not mime_type:
                raise SeedRefused(f"Unsupported file type in manifest: {name}")
            if not path.is_file():
                raise SeedRefused(f"File listed in manifest does not exist: {name}")
            data = path.read_bytes()
            if len(data) > settings.DEMO_MAX_FILE_SIZE:
                raise SeedRefused(f"File is larger than DEMO_MAX_FILE_SIZE: {name}")
            files.append(
                SeedFile(name, mime_type, data, hashlib.sha256(data).hexdigest())
            )
        projects.append(
            SeedProject(project["name"], files, project.get("starterQuestions", []))
        )

    return projects


def ensure_migrated():
    columns = [column["name"] for column in inspect(engine).get_columns("users")]
    if "is_demo" not in columns:
        raise SeedRefused("users.is_demo does not exist. Run: alembic upgrade head")


def get_or_create_demo_user(db: Session, apply: bool) -> User | None:
    demo_user = user_service.get_demo_user(db)
    if demo_user:
        return demo_user

    existing = user_service.get_user_by_email(db, settings.DEMO_USER_EMAIL)
    if existing:
        raise SeedRefused(
            f"{settings.DEMO_USER_EMAIL} belongs to a non-demo user. "
            "Change DEMO_USER_EMAIL; this script will not modify real users."
        )

    logger.info("Creating demo user %s", settings.DEMO_USER_EMAIL)
    if not apply:
        return None

    demo_user = User(
        username="Demo User",
        email=settings.DEMO_USER_EMAIL,
        password_hash=user_service.get_password_hash(secrets.token_urlsafe(48)),
        is_demo=True,
    )
    db.add(demo_user)
    db.commit()
    db.refresh(demo_user)
    return demo_user


def get_or_create_project(
    db: Session,
    demo_user: User,
    seed_project: SeedProject,
    claimed: set[int],
    apply: bool,
) -> Project | None:
    projects = db.scalars(
        select(Project).where(Project.user_id == demo_user.id).order_by(Project.id)
    ).all()

    for project in projects:
        if project.id not in claimed and project.name == seed_project.name:
            return project

    # A visitor may have renamed the seeded project: recognise it by its files.
    file_names = [file.name for file in seed_project.files]
    for project in projects:
        if project.id in claimed:
            continue
        holds_seed_file = db.scalar(
            select(func.count(File.id)).where(
                File.project_id == project.id, File.name.in_(file_names)
            )
        )
        if holds_seed_file:
            logger.info("Restoring project name %r", seed_project.name)
            if apply:
                project.name = seed_project.name
                db.commit()
            return project

    logger.info("Creating project %r", seed_project.name)
    if not apply:
        return None

    project = project_service.create_project(db, demo_user.id, seed_project.name)
    db.commit()
    return project


def file_problem(db: Session, s3, file: File, seed_file: SeedFile) -> str | None:
    if file.status != FileStatus.processed:
        return f"status is {file.status.value}"

    chunks, embedded = db.execute(
        select(func.count(Chunk.id), func.count(Chunk.embedding)).where(
            Chunk.file_id == file.id
        )
    ).one()
    if chunks == 0 or embedded != chunks:
        return "chunks or embeddings are missing"

    try:
        head = s3.head_object(Bucket=settings.AWS_BUCKET_NAME, Key=file.storage_key)
    except ClientError:
        return "object is missing from S3"

    if head["ContentLength"] != len(seed_file.data):
        return "size differs from the example file"
    if head.get("Metadata", {}).get("sha256") != seed_file.sha256:
        return "content differs from the example file"

    return None


def is_in_flight(file: File) -> bool:
    if file.status not in (FileStatus.pending, FileStatus.processing):
        return False
    age = datetime.now(timezone.utc) - file.updated_at
    return age < timedelta(seconds=settings.DEMO_SEED_TIMEOUT_SECONDS)


def purge_file(db: Session, s3, demo_user: User, project: Project, file: File):
    # Only demo-owned rows with keys in this environment's prefix are ever deleted.
    assert demo_user.is_demo
    assert project.user_id == demo_user.id and file.project_id == project.id
    assert file.storage_key.startswith(KEY_PREFIX)

    s3.delete_object(Bucket=settings.AWS_BUCKET_NAME, Key=file.storage_key)
    db.delete(file)
    db.commit()


def ingest_files(
    db: Session,
    s3,
    demo_user: User,
    project: Project,
    seed_files: list[SeedFile],
    failures: list[str],
):
    rows = file_service.create_files(
        db,
        demo_user.id,
        project.id,
        [FileCreate(name=f.name, mime_type=f.mime_type, size=len(f.data)) for f in seed_files],
    )

    confirmations: list[ConfirmUploadRequest] = []
    for row, seed_file in zip(rows, seed_files):
        try:
            s3.put_object(
                Bucket=settings.AWS_BUCKET_NAME,
                Key=row.storage_key,
                Body=seed_file.data,
                ContentType=seed_file.mime_type,
                Metadata={"sha256": seed_file.sha256, "demo-seed": "1"},
            )
            confirmations.append(ConfirmUploadRequest(id=row.id))
        except ClientError as err:
            logger.error("Could not upload %s: %s", seed_file.name, err)
            failures.append(f"{seed_file.name}: upload to S3 failed")
            confirmations.append(
                ConfirmUploadRequest(id=row.id, error="Could not upload")
            )

    files = file_service.confirm_uploads(db, demo_user.id, confirmations)

    if settings.ENVIRONMENT == "production":
        enqueue_files(files, rename_project=False)
    else:
        for file in files:
            try:
                process_files_locally([file], rename_project=False)
            except Exception:
                failures.append(f"{file.name}: processing failed")


def wait_for_processing(file_ids: list[int]):
    deadline = time.monotonic() + settings.DEMO_SEED_TIMEOUT_SECONDS
    while True:
        with SessionLocal() as db:
            unfinished = db.scalar(
                select(func.count(File.id)).where(
                    File.id.in_(file_ids),
                    File.status.in_([FileStatus.pending, FileStatus.processing]),
                )
            )
        if not unfinished:
            return
        if time.monotonic() > deadline:
            logger.warning("Timed out waiting for %s file(s)", unfinished)
            return
        logger.info("Waiting for %s file(s) to finish processing...", unfinished)
        time.sleep(POLL_INTERVAL_SECONDS)


def delete_messages_after(
    db: Session, project: Project, cutoff: datetime, apply: bool
):
    count = db.scalar(
        select(func.count(Message.id)).where(
            Message.project_id == project.id, Message.created_at > cutoff
        )
    )
    logger.info(
        "%s %s message(s) in %r created after %s",
        "Deleting" if apply else "Would delete",
        count,
        project.name,
        cutoff,
    )
    if apply and count:
        # Citations are removed by the database (ON DELETE CASCADE).
        db.execute(
            delete(Message).where(
                Message.project_id == project.id, Message.created_at > cutoff
            )
        )
        db.commit()


def create_starter_chat(
    db: Session, demo_user: User, project: Project, questions: list[str]
) -> bool:
    last_id_before = (
        db.scalar(
            select(func.max(Message.id)).where(Message.project_id == project.id)
        )
        or 0
    )
    try:
        for question in questions:
            logger.info("Asking: %s", question)
            chat_service.send_user_message(db, demo_user.id, project.id, question)
        return True
    except Exception:
        logger.exception("Starter chat failed; removing its partial messages")
        db.rollback()
        db.execute(
            delete(Message).where(
                Message.project_id == project.id, Message.id > last_id_before
            )
        )
        db.commit()
        return False


def seed(
    seed_projects: list[SeedProject],
    apply: bool,
    messages_cutoff: datetime | None,
) -> int:
    failures: list[str] = []
    s3 = file_service.get_s3_client()

    with SessionLocal() as db:
        demo_user = get_or_create_demo_user(db, apply)
        if demo_user is None:
            logger.info("Dry run: nothing exists yet, everything would be created.")
            return EXIT_OK

        claimed: set[int] = set()
        resolved: list[tuple[SeedProject, Project]] = []
        for seed_project in seed_projects:
            project = get_or_create_project(db, demo_user, seed_project, claimed, apply)
            if project is None:
                logger.info("Dry run: would ingest %s file(s)", len(seed_project.files))
                continue
            claimed.add(project.id)
            resolved.append((seed_project, project))

        for seed_project, project in resolved:
            missing = missing_files(db, s3, demo_user, project, seed_project, apply)
            for seed_file in missing:
                logger.info("Will ingest %s into %r", seed_file.name, project.name)
            if apply and missing:
                ingest_files(db, s3, demo_user, project, missing, failures)

        if not apply:
            for seed_project, project in resolved:
                if messages_cutoff:
                    delete_messages_after(db, project, messages_cutoff, apply)
            logger.info("Dry run complete. Re-run with --apply to make changes.")
            return EXIT_OK

        file_ids = [
            file_id
            for _, project in resolved
            for file_id in db.scalars(
                select(File.id).where(File.project_id == project.id)
            ).all()
        ]
        wait_for_processing(file_ids)
        db.expire_all()

        for seed_project, project in resolved:
            healthy = True
            for seed_file in seed_project.files:
                rows = db.scalars(
                    select(File).where(
                        File.project_id == project.id, File.name == seed_file.name
                    )
                ).all()
                problems = [file_problem(db, s3, row, seed_file) for row in rows]
                if not rows or all(problems):
                    healthy = False
                    failures.append(f"{seed_file.name}: not healthy ({problems})")

            if messages_cutoff:
                delete_messages_after(db, project, messages_cutoff, apply)

            message_count = db.scalar(
                select(func.count(Message.id)).where(Message.project_id == project.id)
            )
            if message_count == 0 and seed_project.questions:
                if not healthy:
                    failures.append(f"{project.name}: skipped starter chat")
                elif not create_starter_chat(
                    db, demo_user, project, seed_project.questions
                ):
                    failures.append(f"{project.name}: starter chat failed")

    for failure in failures:
        logger.error("FAILED: %s", failure)
    return EXIT_PARTIAL if failures else EXIT_OK


def missing_files(
    db: Session,
    s3,
    demo_user: User,
    project: Project,
    seed_project: SeedProject,
    apply: bool,
) -> list[SeedFile]:
    """Seed files with no healthy or in-flight copy. Broken copies are purged."""
    missing: list[SeedFile] = []
    rows = db.scalars(select(File).where(File.project_id == project.id)).all()

    for seed_file in seed_project.files:
        same_name = [row for row in rows if row.name == seed_file.name]
        if any(file_problem(db, s3, row, seed_file) is None for row in same_name):
            continue
        if any(is_in_flight(row) for row in same_name):
            continue

        for row in same_name:
            logger.info(
                "Replacing %s (id %s): %s",
                row.name,
                row.id,
                file_problem(db, s3, row, seed_file),
            )
            if apply:
                purge_file(db, s3, demo_user, project, row)
        missing.append(seed_file)

    return missing


def run(apply: bool, messages_cutoff: datetime | None) -> int:
    try:
        seed_projects = load_manifest()
        ensure_migrated()
        logger.info(
            "Target: db=%s bucket=%s environment=%s mode=%s",
            engine.url.render_as_string(hide_password=True),
            settings.AWS_BUCKET_NAME,
            settings.ENVIRONMENT,
            "APPLY" if apply else "DRY RUN",
        )

        with engine.connect() as lock_connection:
            locked = lock_connection.execute(
                text("select pg_try_advisory_lock(:key)"), {"key": ADVISORY_LOCK_KEY}
            ).scalar()
            lock_connection.commit()
            if not locked:
                logger.info("Another seed run is in progress. Exiting.")
                return EXIT_OK
            try:
                return seed(seed_projects, apply, messages_cutoff)
            finally:
                lock_connection.execute(
                    text("select pg_advisory_unlock(:key)"),
                    {"key": ADVISORY_LOCK_KEY},
                )
                lock_connection.commit()
    except SeedRefused as err:
        logger.error("Refusing to run: %s", err)
        return EXIT_REFUSED
