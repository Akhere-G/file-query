import json
from types import SimpleNamespace

import pytest

from src.features.files import embedding_service
from src.features.files.embedding_service import (
    generate_embedding,
    get_response,
    rerank_chunks,
    rewrite_query,
    usage_totals,
)
from src.settings import settings

pytestmark = pytest.mark.unit


def chunk(content):
    return SimpleNamespace(content=content)


class TestGenerateEmbedding:
    def test_requests_a_normalised_1024_dimension_titan_embedding(self, aws_fakes, monkeypatch):
        seen = {}
        original = aws_fakes.bedrock.invoke_model

        def spy(**kwargs):
            seen.update(kwargs)
            return original(**kwargs)

        monkeypatch.setattr(aws_fakes.bedrock, "invoke_model", spy)

        vector = generate_embedding("hello world")

        assert seen["modelId"] == "amazon.titan-embed-text-v2:0"
        assert json.loads(seen["body"]) == {
            "inputText": "hello world",
            "dimensions": 1024,
            "normalize": True,
        }
        assert len(vector) == 1024

    def test_bedrock_errors_propagate(self, aws_fakes):
        aws_fakes.bedrock.embed_error = RuntimeError("throttled")
        with pytest.raises(RuntimeError, match="throttled"):
            generate_embedding("hello")


class TestGetResponse:
    def test_returns_the_first_text_block(self, aws_fakes):
        aws_fakes.bedrock.answer = "The answer"
        assert get_response("question?") == "The answer"

    def test_response_without_text_returns_none(self, aws_fakes, monkeypatch):
        def no_text(**kwargs):
            return {
                "usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2},
                "output": {"message": {"content": [{"toolUse": {}}]}},
            }

        monkeypatch.setattr(aws_fakes.bedrock, "converse", no_text)
        assert get_response("question?") is None

    def test_response_with_no_message_returns_none(self, aws_fakes, monkeypatch):
        def no_message(**kwargs):
            return {
                "usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2},
                "output": {},
            }

        monkeypatch.setattr(aws_fakes.bedrock, "converse", no_message)
        assert get_response("question?") is None

    def test_token_usage_is_accumulated_when_tracked(self, aws_fakes):
        totals = {"input_tokens": 0, "output_tokens": 0}
        token = usage_totals.set(totals)
        try:
            get_response("a")
            get_response("b")
        finally:
            usage_totals.reset(token)
        assert totals == {"input_tokens": 2, "output_tokens": 2}

    def test_uses_the_configured_chat_model(self, aws_fakes, monkeypatch):
        seen = {}
        original = aws_fakes.bedrock.converse

        def spy(**kwargs):
            seen.update(kwargs)
            return original(**kwargs)

        monkeypatch.setattr(aws_fakes.bedrock, "converse", spy)
        get_response("hi")
        assert seen["modelId"] == settings.BEDROCK_CHAT_MODEL_ID


class TestRewriteQuery:
    def test_prompt_contains_the_conversation_and_the_question(self, aws_fakes):
        rewrite_query("what about its price?", "user: tell me about the X100\nassistant: it is a drill")

        prompt = aws_fakes.bedrock.prompts[0]
        assert "user: tell me about the X100" in prompt
        assert "what about its price?" in prompt
        assert "Do not answer the question" in prompt

    def test_returns_the_rewritten_query_trimmed(self, aws_fakes):
        aws_fakes.bedrock.rewrites["what about its price?"] = "  X100 drill price \n"
        assert rewrite_query("what about its price?", "user: X100") == "X100 drill price"

    def test_standalone_question_is_returned_unchanged(self, aws_fakes):
        assert rewrite_query("When was the company founded?", "") == "When was the company founded?"

    @pytest.mark.parametrize("model_reply", [None, ""])
    def test_empty_model_reply_falls_back_to_the_original_question(
        self, aws_fakes, monkeypatch, model_reply
    ):
        monkeypatch.setattr(embedding_service, "get_response", lambda prompt: model_reply)
        assert rewrite_query("original?", "user: hi") == "original?"

    @pytest.mark.xfail(
        strict=True,
        reason="Known gap: a whitespace-only model reply is truthy, so it is stripped to an "
        "empty search query instead of falling back to the original question",
    )
    def test_whitespace_only_model_reply_falls_back_to_the_original_question(
        self, aws_fakes, monkeypatch
    ):
        monkeypatch.setattr(embedding_service, "get_response", lambda prompt: "   ")
        assert rewrite_query("original?", "user: hi") == "original?"

    def test_model_failure_propagates(self, aws_fakes):
        aws_fakes.bedrock.converse_error = RuntimeError("down")
        with pytest.raises(RuntimeError):
            rewrite_query("q", "")


class TestRerank:
    def test_no_chunks_means_no_remote_call(self, aws_fakes):
        assert rerank_chunks("query", []) == []
        assert aws_fakes.agent.calls == []

    def test_results_are_returned_in_the_order_the_reranker_chose(self, aws_fakes):
        aws_fakes.use_semantic()
        chunks = [chunk("bananas are yellow"), chunk("cats purr loudly"), chunk("how cats purr")]

        result = rerank_chunks("why do cats purr", chunks, limit=3)

        assert [c.content for c in result][:2] == ["cats purr loudly", "how cats purr"]
        assert len(result) == 3

    def test_limit_caps_the_number_of_results(self, aws_fakes):
        chunks = [chunk(f"doc {i}") for i in range(10)]
        assert len(rerank_chunks("doc", chunks, limit=4)) == 4

    def test_limit_larger_than_candidates_returns_all_candidates(self, aws_fakes):
        chunks = [chunk("a"), chunk("b")]
        assert len(rerank_chunks("a", chunks, limit=5)) == 2

    def test_query_and_chunk_texts_are_sent_to_the_reranker(self, aws_fakes):
        rerank_chunks("my query", [chunk("first"), chunk("second")])
        assert aws_fakes.agent.calls == [{"query": "my query", "texts": ["first", "second"]}]
