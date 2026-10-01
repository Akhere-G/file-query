import json
import logging

from src.features.files.file_processing_service import get_sqs_client, process_file
from src.settings import settings

logger = logging.getLogger(__name__)


def run_worker():
    sqs = get_sqs_client()

    response = sqs.receive_message(
        QueueUrl=settings.SQS_QUEUE_URL, MaxNumberOfMessages=1, WaitTimeSeconds=20
    )

    for message in response.get("Messages", []):
        try:
            job = json.loads(message["Body"])

            process_file(job)

            sqs.delete_message(
                QueueUrl=settings.SQS_QUEUE_URL, ReceiptHandle=message["ReceiptHandle"]
            )
        except Exception:
            logger.exception("Failed to process SQS message")
