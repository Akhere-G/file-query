import json
import logging

import boto3
from mypy_boto3_bedrock_runtime.client import BedrockRuntimeClient
from src.settings import settings

logger = logging.getLogger(__name__)


def get_bedrock_client() -> BedrockRuntimeClient:
    return boto3.client("bedrock-runtime", region_name=settings.AWS_REGION)  # type: ignore


def generate_embedding(text: str) -> list[float]:
    client = get_bedrock_client()

    response = client.invoke_model(
        modelId="amazon.titan-embed-text-v2:0",
        body=json.dumps({"inputText": text, "dimensions": 1024, "normalize": True}),
        contentType="application/json",
        accept="application/json",
    )
    result = json.loads(response["body"].read())

    return result["embedding"]


def get_response(text: str) -> str:
    client = get_bedrock_client()

    response = client.converse(
        modelId=settings.BEDROCK_CHAT_MODEL_ID,
        messages=[{"role": "user", "content": [{"text": text}]}],
        inferenceConfig={"maxTokens": 1000, "temperature": 0.2},
    )
    usage = response["usage"]

    logger.info(
        "Bedrock usage: input=%s, output=%s, total=%s",
        usage["inputTokens"],
        usage["outputTokens"],
        usage["totalTokens"],
    )

    message = response["output"].get("message", {})
    content = message.get("content", [])

    for block in content:
        if "text" in block:
            return block["text"]

    logger.warning("Bedrock response did not contain text: %s", response)
    return "Sorry, I could not answer your question."
