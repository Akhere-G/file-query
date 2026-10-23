import json
import math
import re
import zlib
from io import BytesIO

from botocore.exceptions import ClientError


class FakeS3:
    def __init__(self):
        self.objects = {}
        self.deleted = []

    def put(self, key, data):
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
        self.sent = []
        self.fail = False

    def send_message(self, QueueUrl, MessageBody):
        if self.fail:
            raise RuntimeError("sqs down")
        self.sent.append(json.loads(MessageBody))


STOPWORDS = frozenset(
    ["a", "an", "and", "are", "as", "at", "be", "by", "do", "does", "for", "from", "how", "i", "in", "is", "it", "its", "of", "on", "or", "that", "the", "this", "to", "was", "what", "when", "where", "which", "who", "why", "with", "you", "your"]
)
EMBEDDING_DIMENSIONS = 1024


def content_terms(text: str) -> list[str]:
    """Lower-cased words minus stopwords, with a crude plural stem."""
    terms = []
    for word in re.findall(r"\w+", text.lower()):
        if word in STOPWORDS:
            continue
        terms.append(word[:-1] if len(word) > 3 and word.endswith("s") else word)
    return terms


def bag_of_words_vector(text: str) -> list[float]:
    """Deterministic embedding: texts sharing words get a real, non-zero cosine similarity."""
    vector = [0.0] * EMBEDDING_DIMENSIONS
    for term in content_terms(text):
        vector[zlib.crc32(term.encode()) % EMBEDDING_DIMENSIONS] += 1.0
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        vector[0], norm = 1.0, 1.0
    return [v / norm for v in vector]


class FakeBedrockRuntime:
    """Default behaviour is unchanged. `semantic=True` switches to bag-of-words embeddings
    and an extractive "LLM" that answers from the retrieved context or refuses."""

    def __init__(self):
        self.embed_calls = 0
        self.converse_calls = 0
        self.answer = "Fake answer."
        self.semantic = False
        self.prompts = []
        self.answer_prompts = []
        self.rewrites = {}
        self.embed_error = None
        self.converse_error = None
        self.embedded_texts = []

    def invoke_model(self, modelId, body, **kwargs):
        self.embed_calls += 1
        if self.embed_error is not None:
            raise self.embed_error
        text = json.loads(body)["inputText"]
        self.embedded_texts.append(text)
        if self.semantic:
            vector = bag_of_words_vector(text)
        else:
            vector = [0.0] * EMBEDDING_DIMENSIONS
            vector[hash(text) % EMBEDDING_DIMENSIONS] = 1.0
            norm = math.sqrt(sum(v * v for v in vector)) or 1.0
            vector = [v / norm for v in vector]
        return {"body": BytesIO(json.dumps({"embedding": vector}).encode())}

    def converse(self, modelId, messages, **kwargs):
        self.converse_calls += 1
        if self.converse_error is not None:
            raise self.converse_error
        prompt = messages[0]["content"][0]["text"]
        self.prompts.append(prompt)
        if "Search query:" in prompt:
            question = prompt.split("User question:")[1].split("Search query:")[0].strip()
            reply = self.rewrites.get(question, question)
        else:
            self.answer_prompts.append(prompt)
            reply = self._extractive_answer(prompt) if self.semantic else self.answer
        return {
            "usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2},
            "output": {"message": {"content": [{"text": reply}]}},
        }

    def _extractive_answer(self, prompt):
        from src.features.files.embedding_service import NO_CONTEXT_RESPONSE

        if "descriptive name for a project" in prompt:
            return "Project Documents"
        question = prompt.split("User question:")[1].split("Context:")[0].strip()
        context = prompt.split("Context:")[1].rsplit("Answer:", 1)[0]
        wanted = set(content_terms(question))
        best, best_score = None, 0
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", context):
            if sentence.strip().startswith(("[Source", "#")):
                continue
            score = len(wanted & set(content_terms(sentence)))
            if score > best_score:
                best, best_score = sentence.strip(), score
        # Answer only when one sentence covers most of the question; otherwise refuse,
        # like a model told to refuse when the context does not really answer the question.
        covered = best_score / len(wanted) if wanted else 0
        return best if best and best_score >= 1 and covered > 0.5 else NO_CONTEXT_RESPONSE


class FakeBedrockAgent:
    """Default keeps the input order. `rerank_by_overlap=True` orders by shared query terms."""

    def __init__(self):
        self.rerank_by_overlap = False
        self.calls = []

    def rerank(self, sources, rerankingConfiguration, **kwargs):
        count = rerankingConfiguration["bedrockRerankingConfiguration"]["numberOfResults"]
        texts = [src["inlineDocumentSource"]["textDocument"]["text"] for src in sources]
        query = kwargs["queries"][0]["textQuery"]["text"]
        self.calls.append({"query": query, "texts": texts})
        order = list(range(len(sources)))
        if self.rerank_by_overlap:
            wanted = set(content_terms(query))
            order.sort(key=lambda i: -len(wanted & set(content_terms(texts[i]))))
        return {"results": [{"index": i, "relevanceScore": 1.0} for i in order[:count]]}


class Fakes:
    def __init__(self):
        self.s3 = FakeS3()
        self.sqs = FakeSQS()
        self.bedrock = FakeBedrockRuntime()
        self.agent = FakeBedrockAgent()

    def use_semantic(self):
        self.bedrock.semantic = True
        self.agent.rerank_by_overlap = True
        return self


def install_fakes(monkeypatch):
    from src import aws

    fakes = Fakes()
    monkeypatch.setattr(aws, "s3_client", lambda: fakes.s3)
    monkeypatch.setattr(aws, "sqs_client", lambda: fakes.sqs)
    monkeypatch.setattr(aws, "bedrock_runtime_client", lambda: fakes.bedrock)
    monkeypatch.setattr(aws, "bedrock_agent_client", lambda: fakes.agent)
    return fakes
