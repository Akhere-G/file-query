from sqlalchemy import delete, select
from src.database import SessionLocal
from src.features.chat.message_model import Citation, Message
from src.features.files.file_model import Chunk, File, FileStatus
from src.features.files.file_processing_service import FileJob, process_file


def main() -> None:
    with SessionLocal() as db:
        db.execute(delete(Citation))
        db.execute(delete(Message))
        db.execute(delete(Chunk))

        files = db.scalars(
            select(File).where(File.status == FileStatus.processing)
        ).all()

        jobs: list[FileJob] = [
            {
                "file_id": file.id,
                "storage_key": file.storage_key,
                "mime_type": file.mime_type,
            }
            for file in files
        ]

        for file in files:
            file.status = FileStatus.processing
            file.error = None

        db.commit()

    for job in jobs:
        print(f"Processing file {job['file_id']}...")

        try:
            process_file(job)
            print(f"Processed file {job['file_id']}")
        except Exception as error:
            print(f"Failed to process file {job['file_id']}: {error}")
            raise


if __name__ == "__main__":
    main()
