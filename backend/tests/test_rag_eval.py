"""Fixed retrieval/answer evaluation.

The corpus in tests/data/rag_corpus is ingested through the real upload -> extract -> chunk ->
embed pipeline, then every case in tests/data/rag_eval.json is asked through the chat API.
The fakes are deterministic, so this checks the *pipeline* (retrieval, ranking, citation and
refusal behaviour), not the quality of a real model. To add a case: add a document sentence
and an entry in rag_eval.json naming the file and the evidence phrase it should surface.
"""

import json
from pathlib import Path

import pytest

from src.features.chat.chat_service import get_relevant_chunks
from src.features.files.embedding_service import NO_CONTEXT_RESPONSE
from tests.helpers import upload_and_confirm

pytestmark = pytest.mark.rag_eval

DATA = Path(__file__).parent / "data"
DATASET = json.loads((DATA / "rag_eval.json").read_text())
REFUSALS = {NO_CONTEXT_RESPONSE, "Sorry, I could not answer your question with the context provided."}


@pytest.fixture
def corpus_project(client, make_user, semantic_aws):
    _, headers = make_user()
    project_id = None
    for path in sorted((DATA / "rag_corpus").glob("*.md")):
        project_id, _, confirm = upload_and_confirm(
            client, semantic_aws, headers, path.name, path.read_bytes(), "text/markdown", project_id
        )
        assert confirm.status_code == 200, confirm.text
    files = client.get(f"/api/projects/{project_id}/files", headers=headers).json()
    assert {f["status"] for f in files} == {"processed"}
    return project_id, headers


def ask(client, project_id, headers, question):
    res = client.post(
        f"/api/projects/{project_id}/messages", json={"content": question}, headers=headers
    )
    assert res.status_code == 200, res.text
    return res.json()


def test_answerable_questions_are_grounded_in_the_expected_source(client, corpus_project):
    project_id, headers = corpus_project
    failures = []

    for case in DATASET["cases"]:
        answer = ask(client, project_id, headers, case["question"])
        cited_files = [c["fileName"] for c in answer["citations"]]
        evidence_found = any(case["expected_evidence"] in c["content"] for c in answer["citations"])
        keywords_found = all(k.lower() in answer["content"].lower() for k in case["answer_keywords"])

        problems = []
        if answer["content"] in REFUSALS:
            problems.append("refused although the corpus contains the answer")
        if case["expected_file"] not in cited_files:
            problems.append(f"expected source not cited (cited: {cited_files})")
        if not evidence_found:
            problems.append("no citation contains the expected evidence chunk")
        if not keywords_found:
            problems.append(f"answer is missing keywords {case['answer_keywords']}")
        if problems:
            failures.append(f"{case['id']}: {'; '.join(problems)}")

    assert not failures, "RAG evaluation regressions:\n" + "\n".join(failures)


def test_expected_evidence_is_ranked_first_by_retrieval(db, corpus_project):
    project_id, _ = corpus_project
    misses = []

    for case in DATASET["cases"]:
        retrieved = get_relevant_chunks(db, project_id, case["question"])
        if not retrieved or case["expected_evidence"] not in retrieved[0].content:
            misses.append(f"{case['id']}: top chunk was {retrieved[0].content[:60]!r}" if retrieved else case["id"])

    assert not misses, "Expected evidence was not the top-ranked chunk:\n" + "\n".join(misses)


@pytest.mark.xfail(
    strict=True,
    reason="Known gap: every reranked chunk is cited (the reranker has no score threshold and "
    "citations are not filtered to the chunks the answer used), so unrelated files get cited",
)
def test_only_supporting_sources_are_cited(client, corpus_project):
    project_id, headers = corpus_project
    for case in DATASET["cases"]:
        answer = ask(client, project_id, headers, case["question"])
        assert {c["fileName"] for c in answer["citations"]} == {case["expected_file"]}, case["id"]


def test_unanswerable_questions_are_refused_without_citations(client, corpus_project):
    project_id, headers = corpus_project
    failures = []

    for case in DATASET["unanswerable"]:
        answer = ask(client, project_id, headers, case["question"])
        if answer["content"] not in REFUSALS or answer["citations"]:
            failures.append(
                f"{case['id']}: answered {answer['content']!r} with {len(answer['citations'])} citations"
            )

    assert not failures, "Unsupported answers given:\n" + "\n".join(failures)


def test_evidence_phrases_in_the_dataset_exist_in_the_corpus():
    """Guards the dataset itself: a typo here would make the evaluation vacuous."""
    corpus = {p.name: p.read_text() for p in (DATA / "rag_corpus").glob("*.md")}
    for case in DATASET["cases"]:
        assert case["expected_evidence"] in corpus[case["expected_file"]], case["id"]
