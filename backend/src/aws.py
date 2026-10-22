"""Shared, lazily created AWS clients.

boto3 clients are thread-safe and expensive to build, so each one is created once
per process and reused. Tests replace these functions with fakes.
"""

from functools import lru_cache

import boto3
from botocore.config import Config
from src.settings import settings

_COMMON = {
    "connect_timeout": 5,
    "read_timeout": 60,
    "retries": {"mode": "adaptive", "max_attempts": 5},
}


def _client(service: str, region: str, **config):
    return boto3.client(
        service,
        region_name=region,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        config=Config(**_COMMON, **config),
    )


@lru_cache
def s3_client():
    return _client(
        "s3",
        settings.AWS_REGION,
        signature_version="s3v4",
        s3={"addressing_style": "virtual"},
    )


@lru_cache
def sqs_client():
    return _client("sqs", settings.AWS_REGION)


@lru_cache
def bedrock_runtime_client():
    return _client("bedrock-runtime", settings.AWS_REGION)


@lru_cache
def bedrock_agent_client():
    return _client("bedrock-agent-runtime", settings.BEDROCK_RERANK_REGION)
