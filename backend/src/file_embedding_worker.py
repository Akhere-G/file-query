import json
import logging

from src.features.files.file_processing_service import process_file

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    for record in event["Records"]:
        try:
            job = json.loads(record["body"])

            logger.info("Processing file: %s", job["file_id"])

            process_file(job)

            logger.info("Successfully processed file: %s", job["file_id"])

        except Exception:
            logger.exception("Failed to process SQS record")

            raise
