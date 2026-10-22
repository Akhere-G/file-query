"""In-memory stand-ins for S3, SQS and Bedrock."""

import json
import math
from io import BytesIO

from botocore.exceptions import ClientError


class FakeS3:
    def __init__(self):
        self.objects: dict[str, bytes] = {}
        self.deleted: list[str] = []

    def put(self, key: str, data: bytes):
        self.objects[key] = data

    def head_object(self, Bucket, Key):
        if Key not in self.objects:
            raise ClientError({"Error": {"Code": "404", "Message": "nf"}}, "HeadObject")
        return {"ContentLength": len(self.objects[Key])}

    def get_object(self, Bucket, Key):
        return {"Body": BytesIO(self.objects[Key])}

    def delete_object(self, Bucket, Key):
        self.deleted.append(Key)
        self.objects.pop(Key, None)

    def generate_presigned_post(self, Bucket, Key, **kwargs):
        return {"url": f"https://s3.test/{Bucket}", "fields": {"key": Key}}

    def generate_presigned_url(self, ClientMethod, Params, ExpiresIn):
        return f"https://s3.test/{Params['Key']}"


class FakeSQS:
    def __init__(self):
        self.sent: list[dict] = []
        self.fail = False

    def send_message(self, QueueUrl, MessageBody):
        if self.fail:
            raise RuntimeError("sqs down")
        self.sent.append(json.loads(MessageBody))


class FakeBedrockRuntime:
    def __init__(self):
        self.embed_calls = 0
        self.converse_calls = 0
        self.answer = "Fake answer."

    def invoke_model(self, modelId, body, **kwargs):
        self.embed_calls += 1
        text = json.loads(body)["inputText"]
        vec = [0.0] * 1024
        vec[hash(text) % 1024] = 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return {"body": BytesIO(json.dumps({"embedding": [v / norm for v in vec]}).encode())}

    def converse(self, modelId, messages, **kwargs):
        self.converse_calls += 1
        return {
            "usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2},
            "output": {"message": {"content": [{"text": self.answer}]}},
        }


class FakeBedrockAgent:
    def rerank(self, sources, rerankingConfiguration, **kwargs):
        n = rerankingConfiguration["bedrockRerankingConfiguration"]["numberOfResults"]
        return {"results": [{"index": i} for i in range(min(n, len(sources)))]}


class Fakes:
    def __init__(self):
        self.s3 = FakeS3()
        self.sqs = FakeSQS()
        self.bedrock = FakeBedrockRuntime()
        self.agent = FakeBedrockAgent()


def install_fakes(monkeypatch) -> Fakes:
    from src import aws

    fakes = Fakes()
    monkeypatch.setattr(aws, "s3_client", lambda: fakes.s3)
    monkeypatch.setattr(aws, "sqs_client", lambda: fakes.sqs)
    monkeypatch.setattr(aws, "bedrock_runtime_client", lambda: fakes.bedrock)
    monkeypatch.setattr(aws, "bedrock_agent_client", lambda: fakes.agent)
    return fakes
