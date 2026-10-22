from functools import lru_cache

import boto3
from botocore.config import Config
from src.settings import settings

CLIENT_CONFIG = {
    "connect_timeout": 5,
    "read_timeout": 60,
    "retries": {"mode": "adaptive", "max_attempts": 5},
}


@lru_cache
def s3_client():
    return boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "virtual"},
            **CLIENT_CONFIG,
        ),
    )


@lru_cache
def sqs_client():
    return boto3.client(
        "sqs", region_name=settings.AWS_REGION, config=Config(**CLIENT_CONFIG)
    )


@lru_cache
def bedrock_runtime_client():
    return boto3.client(
        "bedrock-runtime", region_name=settings.AWS_REGION, config=Config(**CLIENT_CONFIG)
    )


@lru_cache
def bedrock_agent_client():
    return boto3.client(
        "bedrock-agent-runtime", region_name="eu-central-1", config=Config(**CLIENT_CONFIG)
    )
