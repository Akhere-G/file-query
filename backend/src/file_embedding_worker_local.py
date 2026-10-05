import argparse

from sqlalchemy import select
from src.database import SessionLocal
from src.features.files.file_model import File
from src.features.files.file_processing_service import FileJob, process_file


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file_id", type=int)
    args = parser.parse_args()

    db = SessionLocal()

    try:
        stmt = select(File).where(File.id == args.file_id)
        file = db.execute(stmt).scalar_one_or_none()
        if not file:
            raise FileNotFoundError("File does not exist")
        job: FileJob = {
            "storage_key": file.storage_key,
            "mime_type": file.mime_type,
            "file_id": file.id,
        }
        process_file(job)
    finally:
        if db:
            db.close()


if __name__ == "__main__":
    main()
