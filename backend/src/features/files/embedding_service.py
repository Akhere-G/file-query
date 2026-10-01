import json

import boto3
from src.settings import settings


def get_bedrock_client():
    return boto3.client("bedrock-runtime", region_name=settings.AWS_REGION)


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
