from types import SimpleNamespace

import pytest

from src.features.chat import chat_service
from src.features.chat.chat_service import (
    get_relevant_chunks,
    get_relevant_chunks_by_keywords,
    get_relevant_chunks_by_semantics,
)
from src.settings import settings
from tests.helpers import add_file_with_chunks, add_project

DOG = "The office dog policy allows dogs on Fridays if they are friendly."
REVENUE = "Quarterly revenue grew twelve percent compared with last year."
LEAVE = "Employees receive twenty five days of annual leave."


@pytest.fixture
def owner(client, make_user):
    return make_user()[0]


@pytest.fixture
def project(db, owner):
    project_id = add_project(db, owner["id"])
    add_file_with_chunks(db, project_id, [DOG, REVENUE, LEAVE], name="handbook.md")
    return project_id


def contents(chunks):
    return [chunk.content for chunk in chunks]


class TestKeywordSearch:
    def test_matches_on_stemmed_words(self, db, project):
        # "dogs" in the question matches "dog" and "dogs" in the chunk
        assert contents(get_relevant_chunks_by_keywords(db, project, "dogs")) == [DOG]

    def test_any_term_matching_is_enough(self, db, project):
        result = get_relevant_chunks_by_keywords(db, project, "revenue leave")
        assert set(contents(result)) == {REVENUE, LEAVE}

    def test_chunks_matching_more_terms_rank_higher(self, db, owner):
        project_id = add_project(db, owner["id"])
        add_file_with_chunks(
            db,
            project_id,
            ["Parking is available for visitors.", "Visitors parking requires a permit and a visitors badge."],
        )
        result = get_relevant_chunks_by_keywords(db, project_id, "visitors parking permit")
        assert contents(result)[0].startswith("Visitors parking requires")

    @pytest.mark.parametrize("query", ["", "   ", "!!! ???", "the and of"])
    def test_queries_without_searchable_terms_return_nothing(self, db, project, query):
        assert get_relevant_chunks_by_keywords(db, project, query) == []

    def test_unmatched_query_returns_nothing(self, db, project):
        assert get_relevant_chunks_by_keywords(db, project, "zebra") == []

    @pytest.mark.parametrize("query", ["'; DROP TABLE chunks; --", "a & b | !c", "dog:* <-> (", "\\"])
    def test_special_characters_cannot_break_the_query(self, db, project, query):
        get_relevant_chunks_by_keywords(db, project, query)
        assert get_relevant_chunks_by_keywords(db, project, "dog")

    def test_limit_is_applied(self, db, owner):
        project_id = add_project(db, owner["id"])
        add_file_with_chunks(db, project_id, [f"Gadget number {i}." for i in range(5)])
        assert len(get_relevant_chunks_by_keywords(db, project_id, "gadget", limit=2)) == 2


class TestSemanticSearch:
    def test_most_similar_chunk_is_first(self, db, project, semantic_aws):
        result = get_relevant_chunks_by_semantics(db, project, "what is the dog policy on fridays")
        assert contents(result)[0] == DOG

    def test_unrelated_queries_fall_below_the_similarity_threshold(self, db, project, semantic_aws):
        assert get_relevant_chunks_by_semantics(db, project, "zebra migration patterns") == []

    def test_a_stricter_threshold_filters_out_weaker_matches(self, db, project, semantic_aws, monkeypatch):
        query = "dog policy"
        assert DOG in contents(get_relevant_chunks_by_semantics(db, project, query))
        monkeypatch.setattr(settings, "RAG_SIMILARITY_THRESHOLD", 0.99)
        assert get_relevant_chunks_by_semantics(db, project, query) == []

    def test_chunks_without_an_embedding_are_never_returned(self, db, owner, semantic_aws):
        project_id = add_project(db, owner["id"])
        add_file_with_chunks(db, project_id, [DOG], embed=False)
        assert get_relevant_chunks_by_semantics(db, project_id, DOG) == []

    def test_limit_is_applied(self, db, owner, semantic_aws):
        project_id = add_project(db, owner["id"])
        add_file_with_chunks(db, project_id, [f"Gadget manual part {i}." for i in range(5)])
        assert len(get_relevant_chunks_by_semantics(db, project_id, "gadget manual", limit=2)) == 2


class TestHybridRanking:
    @pytest.fixture
    def stubbed(self, monkeypatch):
        """Replace both searches and the reranker to test only the fusion rules."""
        state = SimpleNamespace(semantic=[], keyword=[], reranked_with=None)

        monkeypatch.setattr(chat_service, "get_relevant_chunks_by_semantics", lambda *a, **k: state.semantic)
        monkeypatch.setattr(chat_service, "get_relevant_chunks_by_keywords", lambda *a, **k: state.keyword)

        def identity_rerank(query, chunks, limit):
            state.reranked_with = SimpleNamespace(query=query, chunks=chunks, limit=limit)
            return chunks[:limit]

        monkeypatch.setattr(chat_service, "rerank_chunks", identity_rerank)
        return state

    @staticmethod
    def chunk(chunk_id):
        return SimpleNamespace(id=chunk_id)

    def test_chunks_found_by_both_searches_outrank_chunks_found_by_one(self, stubbed):
        a, b, c = self.chunk(1), self.chunk(2), self.chunk(3)
        stubbed.semantic = [a, b]
        stubbed.keyword = [c, b]

        get_relevant_chunks(None, 1, "q")

        assert [x.id for x in stubbed.reranked_with.chunks][0] == 2

    def test_rank_position_decides_between_single_list_hits(self, stubbed):
        a, b = self.chunk(1), self.chunk(2)
        stubbed.semantic = [a]
        stubbed.keyword = [b]
        get_relevant_chunks(None, 1, "q")
        # equal reciprocal-rank scores keep the semantic hit first
        assert [x.id for x in stubbed.reranked_with.chunks] == [1, 2]

    def test_candidate_limit_truncates_before_reranking(self, stubbed):
        stubbed.semantic = [self.chunk(i) for i in range(1, 6)]
        get_relevant_chunks(None, 1, "q", candidate_limit=3)
        assert [x.id for x in stubbed.reranked_with.chunks] == [1, 2, 3]

    def test_reranker_gets_the_search_query_and_final_limit(self, stubbed):
        stubbed.keyword = [self.chunk(1)]
        get_relevant_chunks(None, 1, "my question", limit=2)
        assert stubbed.reranked_with.query == "my question"
        assert stubbed.reranked_with.limit == 2

    def test_retrieval_counts_are_reported(self, stubbed):
        stubbed.semantic = [self.chunk(1), self.chunk(2)]
        stubbed.keyword = [self.chunk(2)]
        stats = {}
        get_relevant_chunks(None, 1, "q", stats=stats)
        assert stats == {"semantic": 2, "keyword": 1}

    def test_no_hits_means_no_results(self, stubbed):
        assert get_relevant_chunks(None, 1, "q") == []


class TestEndToEndRetrieval:
    def test_reranker_decides_the_final_order(self, db, owner, semantic_aws):
        project_id = add_project(db, owner["id"])
        add_file_with_chunks(
            db,
            project_id,
            [
                "Refunds are possible. Contact support about a refund.",
                "Refund window: refunds are accepted within thirty days of purchase.",
            ],
        )
        result = get_relevant_chunks(db, project_id, "how many days to get a refund")
        assert contents(result)[0].startswith("Refund window")

    def test_unrelated_question_retrieves_nothing(self, db, project, semantic_aws):
        assert get_relevant_chunks(db, project, "zebra migration patterns") == []

    def test_project_without_files_retrieves_nothing(self, db, owner, semantic_aws):
        assert get_relevant_chunks(db, add_project(db, owner["id"]), "dog policy") == []

    def test_final_result_size_is_capped(self, db, owner, semantic_aws):
        project_id = add_project(db, owner["id"])
        add_file_with_chunks(db, project_id, [f"Widget specification {i}." for i in range(12)])
        assert len(get_relevant_chunks(db, project_id, "widget specification")) == settings.RAG_RERANK_K


class TestProjectIsolation:
    """Identical content in several projects must never leak between them."""

    def test_other_users_identical_documents_are_never_retrieved(self, db, make_user, semantic_aws):
        alice, _ = make_user()
        bob, _ = make_user()
        alice_project = add_project(db, alice["id"])
        bob_project = add_project(db, bob["id"])
        _, alice_chunks = add_file_with_chunks(db, alice_project, [DOG], name="alice.md")
        _, bob_chunks = add_file_with_chunks(db, bob_project, [DOG], name="bob.md")

        for search in (
            get_relevant_chunks,
            get_relevant_chunks_by_keywords,
            get_relevant_chunks_by_semantics,
        ):
            assert [c.id for c in search(db, alice_project, "dog policy")] == alice_chunks
            assert [c.id for c in search(db, bob_project, "dog policy")] == bob_chunks

    def test_a_users_other_project_is_not_searched(self, db, owner, semantic_aws):
        first = add_project(db, owner["id"], "first")
        second = add_project(db, owner["id"], "second")
        add_file_with_chunks(db, first, [DOG])
        add_file_with_chunks(db, second, [REVENUE])

        assert get_relevant_chunks(db, second, "dog policy") == []
        assert contents(get_relevant_chunks(db, first, "dog policy")) == [DOG]

    def test_unique_content_in_another_project_is_invisible(self, db, make_user, semantic_aws):
        alice, _ = make_user()
        bob, _ = make_user()
        add_file_with_chunks(db, add_project(db, alice["id"]), ["The secret launch codename is Bluebird."])
        bob_project = add_project(db, bob["id"])
        add_file_with_chunks(db, bob_project, [LEAVE])

        assert get_relevant_chunks(db, bob_project, "secret launch codename") == []
