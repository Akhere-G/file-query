import json

from src.features.files.file_processing_service import process_file


def handler(event, context):
    for record in event["Records"]:
        job = json.loads(record["body"])
        process_file(job)
