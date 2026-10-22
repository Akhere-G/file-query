import argparse

from sqlalchemy import delete, func, select
from src.database import SessionLocal, engine
from src.features.chat.message_model import Citation, Message
from src.features.files.file_model import Chunk, File, FileStatus
from src.features.files.file_processing_service import FileJob, process_file
from src.settings import settings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Delete ALL chat messages and chunks, then re-embed every processed file."
    )
    parser.add_argument("--apply", action="store_true", help="make changes")
    args = parser.parse_args()

    print(f"Target: {engine.url.render_as_string(hide_password=True)} ({settings.ENVIRONMENT})")
    if settings.ENVIRONMENT == "production":
        print("Refusing to run against production.")
        return 2

    with SessionLocal() as db:
        if not args.apply:
            count = db.scalar(select(func.count(File.id)).where(File.status == FileStatus.processed))
            print(f"Would delete all messages and chunks and reprocess {count} file(s). Use --apply.")
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
                "is_last": False,
            }
            for file in files
        ]

        for file in files:
            file.status = FileStatus.processing
            file.error = None

        db.commit()

    for job in jobs:
        print(f"Processing file {job['file_id']}...")
        process_file(job)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
