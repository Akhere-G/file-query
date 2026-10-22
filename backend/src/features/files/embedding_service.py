import json
import logging
from contextvars import ContextVar

from mypy_boto3_bedrock_agent_runtime.client import (
    AgentsforBedrockRuntimeClient,
)
from mypy_boto3_bedrock_runtime.client import BedrockRuntimeClient
from src import aws
from src.features.files.file_model import Chunk
from src.settings import settings

logger = logging.getLogger(__name__)

NO_CONTEXT_RESPONSE = (
    "I don't have enough information in the provided documents to answer that."
)


def get_bedrock_agent_client() -> AgentsforBedrockRuntimeClient:
    return aws.bedrock_agent_client()  # type: ignore


usage_totals: ContextVar[dict[str, int] | None] = ContextVar(
    "usage_totals", default=None
)


def get_bedrock_client() -> BedrockRuntimeClient:
    return aws.bedrock_runtime_client()  # type: ignore


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


def get_response(text: str) -> str | None:
    client = get_bedrock_client()

    response = client.converse(
        modelId=settings.BEDROCK_CHAT_MODEL_ID,
        messages=[{"role": "user", "content": [{"text": text}]}],
        inferenceConfig={"maxTokens": 1000, "temperature": 0.2},
    )
    usage = response["usage"]

    totals = usage_totals.get()
    if totals is not None:
        totals["input_tokens"] += usage["inputTokens"]
        totals["output_tokens"] += usage["outputTokens"]

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
    return None


def rewrite_query(
    message: str,
    conversation: str,
) -> str:
    prompt = f"""
You rewrite user questions into standalone search queries for document retrieval.

Use the conversation only to resolve ambiguity or missing context.

Rules:
- Use the conversation to resolve references and ambiguity.
- You may use facts explicitly stated in previous user or assistant messages.
- Do not introduce new facts that are not established in the conversation.
- Resolve references such as "it", "they", "that", and "the other one" using the conversation when possible.
- If the question is already clear and standalone, return it unchanged.
- If the conversation does not provide enough information to resolve an ambiguous question, return the original question unchanged.
- Do not answer the question.
- Return only the rewritten search query.

Conversation:
{conversation}

User question:
{message}

Search query:
"""

    return (get_response(prompt) or message).strip()


def rerank_chunks(
    query: str,
    chunks: list[Chunk],
    limit: int = 5,
) -> list[Chunk]:
    if not chunks:
        return []

    client = get_bedrock_agent_client()

    number_of_results = min(limit, len(chunks))

    response = client.rerank(
        queries=[{"type": "TEXT", "textQuery": {"text": query}}],
        sources=[
            {
                "type": "INLINE",
                "inlineDocumentSource": {
                    "type": "TEXT",
                    "textDocument": {
                        "text": chunk.content,
                    },
                },
            }
            for chunk in chunks
        ],
        rerankingConfiguration={
            "type": "BEDROCK_RERANKING_MODEL",
            "bedrockRerankingConfiguration": {
                "modelConfiguration": {
                    "modelArn": (
                        "arn:aws:bedrock:eu-central-1::"
                        "foundation-model/cohere.rerank-v3-5:0"
                    ),
                },
                "numberOfResults": number_of_results,
            },
        },
    )

    return [chunks[result["index"]] for result in response["results"]]
