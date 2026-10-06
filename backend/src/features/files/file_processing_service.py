import enum
import json
import logging
from typing import TypedDict

import boto3
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)
from mypy_boto3_sqs.client import SQSClient
from sqlalchemy import select
from src.database import get_db
from src.features.auth.user_model import User
from src.features.chat.message_model import Citation, Message
from src.features.files.embedding_service import generate_embedding
from src.features.files.file_extraction_service import extract_file
from src.features.files.file_model import Chunk, File, FileStatus
from src.features.files.file_service import get_s3_client
from src.settings import settings

logger = logging.getLogger(__name__)


class SplitType(enum.Enum):
    markdown = "markdown"
    text = "text"


mime_types = {
    "application/msword": SplitType.text,
    "text/plain": SplitType.text,
    "text/csv": SplitType.text,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": SplitType.markdown,
    "application/pdf": SplitType.markdown,
    "text/markdown": SplitType.markdown,
}


def get_sqs_client() -> SQSClient:
    return boto3.client(
        "sqs",
        region_name=settings.AWS_REGION,
    )  # type: ignore


def enqueue_files(files: list[File]):
    sqs = get_sqs_client()
    for file in files:
        logger.info(f"enqueuing file: {file.id}")
        sqs.send_message(
            QueueUrl=settings.SQS_QUEUE_URL,
            MessageBody=json.dumps(
                {
                    "file_id": file.id,
                    "storage_key": file.storage_key,
                    "mime_type": file.mime_type,
                }
            ),
        )


class FileJob(TypedDict):
    file_id: int
    storage_key: str
    mime_type: str


def process_file(job: FileJob):
    file_bytes = download_file(job["storage_key"])
    text = extract_file(file_bytes, job["mime_type"])
    chunks = chunk_text(text)

    process_embeddings(
        file_id=job["file_id"],
        chunks=chunks,
    )


def process_files_locally(files: list[File]):
    for file in files:
        try:
            process_file(
                {
                    "file_id": file.id,
                    "storage_key": file.storage_key,
                    "mime_type": file.mime_type,
                }
            )
        except Exception as err:
            logger.error(f"Could not process file: {file.id}. Error: {err}")
            raise


def download_file(storage_key: str) -> bytes:
    logger.info(f"downloading file: {storage_key}")
    s3 = get_s3_client()

    response = s3.get_object(
        Bucket=settings.AWS_BUCKET_NAME,
        Key=storage_key,
    )

    return response["Body"].read()


def chunk_file(
    text: str,
    mime_type: str,
) -> list[str]:

    if mime_types.get(mime_type) == SplitType.markdown:
        return chunk_markdown(text)
    if mime_types.get(mime_type) == SplitType.text:
        return chunk_text(text)
    logger.warning(f"Default text chunking selected. File has mime type: {mime_type}")
    return chunk_text(text)


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


def chunk_text(
    text: str,
    chunk_size: int = 1500,
    chunk_overlap: int = 200,
) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    return splitter.split_text(text)


def chunk_markdown(
    text: str,
    chunk_size: int = 1500,
    chunk_overlap: int = 200,
) -> list[str]:
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
            ("####", "Header 4"),
        ],
        strip_headers=False,
    )

    sections = header_splitter.split_text(text)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    chunks = []

    for section in sections:
        chunks.extend(splitter.split_text(section.page_content))

    return chunks


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
    logger.warning(f"processing file: {file_id}")

    db = next(get_db())
    file = None

    try:
        file = get_file(db, file_id)

        if file.status == FileStatus.processed:
            logger.warning(
                f"Trying to process file that's already processed: {file_id}"
            )
            return

        chunk_records = create_chunks(file_id, chunks)

        db.add_all(chunk_records)

        file.status = FileStatus.processed
        file.error = None
        db.commit()

    except Exception as err:
        db.rollback()

        logger.error(f"Error processing file: {file_id}")
        logger.error(f"Processing error for {file_id}: {err}")
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
