"""Delete every chat message and chunk, then re-embed all processed files.

This wipes ALL users' chats. It refuses to run when ENVIRONMENT is "production".

Usage (from backend/):
    python -m src.scripts.reprocess_all            # prints the target, changes nothing
    python -m src.scripts.reprocess_all --apply
"""

import argparse
import logging

from sqlalchemy import delete, func, select
from src.database import SessionLocal, engine
from src.features.chat.message_model import Citation, Message
from src.features.files.file_model import Chunk, File, FileStatus
from src.features.files.file_processing_service import FileJob, process_file
from src.settings import settings

logger = logging.getLogger("reprocess_all")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="make changes")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger.info(
        "Target: db=%s environment=%s",
        engine.url.render_as_string(hide_password=True),
        settings.ENVIRONMENT,
    )
    if settings.ENVIRONMENT == "production":
        logger.error("Refusing to run against production.")
        return 2

    with SessionLocal() as db:
        processed = db.scalar(
            select(func.count(File.id)).where(File.status == FileStatus.processed)
        )
        if not args.apply:
            logger.info("Would delete all messages/chunks and reprocess %s file(s). Re-run with --apply.", processed)
            return 0

        db.execute(delete(Citation))
        db.execute(delete(Message))
        db.execute(delete(Chunk))

        files = db.scalars(select(File).where(File.status == FileStatus.processed)).all()
        jobs: list[FileJob] = [
            {
                "file_id": file.id,
                "storage_key": file.storage_key,
                "mime_type": file.mime_type,
                "project_id": file.project_id,
                "rename_project": False,
            }
            for file in files
        ]
        for file in files:
            file.status = FileStatus.processing
            file.error = None
        db.commit()

    for job in jobs:
        logger.info("Processing file %s...", job["file_id"])
        process_file(job)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
