import json
import logging

import boto3
from sqlalchemy import select
from src.database import get_db
from src.features.auth.user_model import User
from src.features.chat.message_model import Message
from src.features.files.embedding_service import generate_embedding
from src.features.files.file_model import Chunk, File, FileStatus
from src.features.files.file_service import get_s3_client
from src.settings import settings

logger = logging.getLogger(__name__)

EXTRACTION_METHODS = {
    "text/plain": lambda file: file.decode("utf-8"),
}


def get_sqs_client():
    return boto3.client(
        "sqs",
        region_name=settings.AWS_REGION,
    )


def enqueue_files(files: list[File]):
    sqs = get_sqs_client()

    for file in files:
        sqs.send_message(
            QueueUrl=settings.SQS_QUEUE_URL,
            MessageBody=json.dumps(
                {
                    "file_id": file.id,
                    "project_id": file.project_id,
                    "storage_key": file.storage_key,
                    "mime_type": file.mime_type,
                }
            ),
        )


def process_file(job):
    file_bytes = download_file(job["storage_key"])
    text = extract_text(file_bytes, job["mime_type"])
    chunks = chunk_text(text)

    process_embeddings(
        file_id=job["file_id"],
        chunks=chunks,
    )


def download_file(storage_key: str) -> bytes:
    s3 = get_s3_client()

    response = s3.get_object(
        Bucket=settings.AWS_BUCKET_NAME,
        Key=storage_key,
    )

    return response["Body"].read()


def extract_text(file: bytes, mime_type: str) -> str:
    extraction_method = EXTRACTION_METHODS.get(mime_type)

    if not extraction_method:
        raise ValueError(f"Unsupported file type: {mime_type}")

    return extraction_method(file)


def chunk_text(
    text: str,
    chunk_size: int = 500,
    offset: int = 100,
) -> list[str]:
    chunks = []
    step = chunk_size - offset

    for i in range(0, len(text), step):
        chunks.append(text[i : i + chunk_size])

    return chunks


def get_file(db, file_id: int) -> File:
    stmt = select(File).where(File.id == file_id)
    file = db.execute(stmt).scalar_one_or_none()

    if not file:
        raise FileNotFoundError(f"File {file_id} not found")

    if file.status == FileStatus.processed:
        logger.warning("File %s has already been processed", file_id)
        return file

    if file.status not in [FileStatus.processing, FileStatus.error]:
        raise ValueError(
            f"File {file_id} cannot be processed in its current state: {file.status}"
        )

    return file


def create_chunks(file_id: int, chunks: list[str]) -> list[Chunk]:
    return [
        Chunk(
            file_id=file_id,
            content=content,
            embedding=generate_embedding(content),
        )
        for content in chunks
    ]


def process_embeddings(file_id: int, chunks: list[str]):
    db = next(get_db())
    file = None

    try:
        file = get_file(db, file_id)

        if file.status == FileStatus.processed:
            return

        chunk_records = create_chunks(file_id, chunks)

        db.add_all(chunk_records)

        file.status = FileStatus.processed
        file.error = None
        db.commit()

    except Exception:
        db.rollback()

        if file:
            try:
                file.status = FileStatus.error
                file.error = "Could not process file"
                db.commit()
            except Exception:
                db.rollback()
                logger.exception(
                    "Failed to mark file %s as errored",
                    file_id,
                )

        raise

    finally:
        db.close()
