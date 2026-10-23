"""Upload -> SQS -> Lambda worker -> database, with S3/SQS/Bedrock faked.

In production /api/files/confirm only enqueues one SQS message per file; the Lambda handler
(`file_embedding_worker.handler`) then processes them. These tests drive both halves, including
the at-least-once delivery behaviour SQS gives us: duplicates, retries and partial batches.
"""

import json

import pytest

from src import file_embedding_worker as worker
from src.features.files.file_model import (
    DEFAULT_PROJECT_NAME,
    Chunk,
    File,
    FileStatus,
    Project,
)
from src.settings import settings
from tests.helpers import upload_and_confirm

TEXT = b"# Pricing\n\nThe starter plan costs nine euros per month.\n\n# Support\n\nSupport answers within one day."


@pytest.fixture
def production(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")


@pytest.fixture
def flushes(monkeypatch):
    calls = []
    monkeypatch.setattr(worker.analytics, "flush", lambda: calls.append(1))
    return calls


@pytest.fixture
def headers(make_user):
    return make_user()[1]


def event(*jobs):
    return {"Records": [{"body": json.dumps(job)} for job in jobs]}


def upload_batch(client, aws_fakes, headers, files, project_id=None):
    """Upload and confirm several files in one request; returns (project_id, file ids)."""
    url = "/api/files" + (f"?project_id={project_id}" if project_id else "")
    res = client.post(
        url,
        json=[{"name": n, "mimeType": m, "size": len(d)} for n, d, m in files],
        headers=headers,
    )
    assert res.status_code == 200, res.text
    for presigned, (_, data, _) in zip(res.json()["files"], files):
        aws_fakes.s3.put(presigned["key"], data)
    ids = [f["id"] for f in res.json()["files"]]
    confirm = client.post("/api/files/confirm", json=[{"id": i} for i in ids], headers=headers)
    assert confirm.status_code == 200, confirm.text
    return res.json()["projectId"], ids


def file_state(db, file_id):
    db.expire_all()
    file = db.get(File, file_id)
    return file.status, file.error, db.query(Chunk).filter_by(file_id=file_id).count()


class TestEnqueueing:
    def test_confirming_an_upload_only_queues_work_and_leaves_the_file_processing(
        self, client, db, aws_fakes, headers, production
    ):
        _, ids = upload_batch(client, aws_fakes, headers, [("a.md", TEXT, "text/markdown")])

        assert file_state(db, ids[0]) == (FileStatus.processing, None, 0)
        assert len(aws_fakes.sqs.sent) == 1

    def test_one_message_per_file_with_the_data_the_worker_needs(
        self, client, db, aws_fakes, headers, production
    ):
        project_id, ids = upload_batch(
            client,
            aws_fakes,
            headers,
            [("a.md", TEXT, "text/markdown"), ("b.txt", b"plain words", "text/plain")],
        )

        first, second = aws_fakes.sqs.sent
        assert [first["file_id"], second["file_id"]] == ids
        assert {first["project_id"], second["project_id"]} == {project_id}
        assert (first["mime_type"], second["mime_type"]) == ("text/markdown", "text/plain")
        assert db.get(File, ids[0]).storage_key == first["storage_key"]

    def test_only_the_last_message_asks_for_the_project_to_be_named(
        self, client, aws_fakes, headers, production
    ):
        upload_batch(
            client,
            aws_fakes,
            headers,
            [(f"{n}.txt", b"some words", "text/plain") for n in "abc"],
        )

        assert [m["is_last"] for m in aws_fakes.sqs.sent] == [False, False, True]

    def test_nothing_is_embedded_by_the_web_request(self, client, aws_fakes, headers, production):
        upload_batch(client, aws_fakes, headers, [("a.md", TEXT, "text/markdown")])
        assert aws_fakes.bedrock.embed_calls == 0


class TestWorker:
    def test_a_queued_file_is_processed_into_searchable_chunks(
        self, client, db, aws_fakes, headers, production, flushes
    ):
        _, ids = upload_batch(client, aws_fakes, headers, [("a.md", TEXT, "text/markdown")])

        worker.handler(event(*aws_fakes.sqs.sent), None)

        status, error, chunk_count = file_state(db, ids[0])
        assert (status, error) == (FileStatus.processed, None)
        assert chunk_count >= 1
        chunk = db.query(Chunk).filter_by(file_id=ids[0]).first()
        assert "starter plan costs nine euros" in chunk.content
        assert chunk.title == "Pricing"
        assert len(chunk.embedding) == 1024
        assert flushes == [1]

    def test_the_project_is_named_after_the_last_file_is_processed(
        self, client, db, aws_fakes, headers, production
    ):
        aws_fakes.bedrock.answer = '"Pricing and Support Notes"'
        project_id, _ = upload_batch(client, aws_fakes, headers, [("a.md", TEXT, "text/markdown")])
        assert db.get(Project, project_id).name == DEFAULT_PROJECT_NAME

        worker.handler(event(*aws_fakes.sqs.sent), None)

        db.expire_all()
        assert db.get(Project, project_id).name == "Pricing and Support Notes"

    def test_a_whole_batch_of_records_is_processed(self, client, db, aws_fakes, headers, production):
        _, ids = upload_batch(
            client,
            aws_fakes,
            headers,
            [("a.md", TEXT, "text/markdown"), ("b.txt", b"second file", "text/plain")],
        )

        worker.handler(event(*aws_fakes.sqs.sent), None)

        assert [file_state(db, i)[0] for i in ids] == [FileStatus.processed] * 2

    def test_a_duplicate_delivery_does_not_duplicate_chunks(
        self, client, db, aws_fakes, headers, production
    ):
        _, ids = upload_batch(client, aws_fakes, headers, [("a.md", TEXT, "text/markdown")])
        job = aws_fakes.sqs.sent[0]

        worker.handler(event(job), None)
        _, _, chunks_after_first = file_state(db, ids[0])
        embeds_after_first = aws_fakes.bedrock.embed_calls
        worker.handler(event(job), None)

        assert file_state(db, ids[0]) == (FileStatus.processed, None, chunks_after_first)
        assert aws_fakes.bedrock.embed_calls == embeds_after_first

    def test_the_same_message_twice_in_one_batch_is_safe(self, client, db, aws_fakes, headers, production):
        _, ids = upload_batch(client, aws_fakes, headers, [("a.md", TEXT, "text/markdown")])
        job = aws_fakes.sqs.sent[0]

        worker.handler(event(job, job), None)

        status, _, chunks = file_state(db, ids[0])
        assert status == FileStatus.processed
        assert chunks == 1


class TestFailureHandling:
    def test_an_unreadable_file_is_marked_as_an_error_and_not_retried(
        self, client, db, aws_fakes, headers, production, flushes
    ):
        _, ids = upload_batch(client, aws_fakes, headers, [("bad.pdf", b"not a pdf", "application/pdf")])

        worker.handler(event(*aws_fakes.sqs.sent), None)  # must not raise: retrying cannot help

        status, error, chunks = file_state(db, ids[0])
        assert status == FileStatus.error
        assert "couldn't read" in error
        assert chunks == 0
        assert aws_fakes.bedrock.embed_calls == 0
        assert flushes == [1]

    def test_a_file_missing_from_storage_becomes_an_error(
        self, client, db, aws_fakes, headers, production
    ):
        _, ids = upload_batch(client, aws_fakes, headers, [("a.md", TEXT, "text/markdown")])
        job = aws_fakes.sqs.sent[0]
        aws_fakes.s3.objects.pop(job["storage_key"])

        worker.handler(event(job), None)

        assert file_state(db, ids[0])[0] == FileStatus.error

    def test_an_embedding_outage_fails_the_message_so_sqs_retries_it(
        self, client, db, aws_fakes, headers, production, flushes
    ):
        _, ids = upload_batch(client, aws_fakes, headers, [("a.md", TEXT, "text/markdown")])
        aws_fakes.bedrock.embed_error = RuntimeError("bedrock throttled")

        with pytest.raises(RuntimeError, match="throttled"):
            worker.handler(event(*aws_fakes.sqs.sent), None)

        status, error, chunks = file_state(db, ids[0])
        assert (status, error, chunks) == (FileStatus.error, "Could not process file", 0)
        assert flushes == [1]  # events are flushed even when the invocation fails

    def test_redelivery_after_the_outage_recovers_the_file(
        self, client, db, aws_fakes, headers, production
    ):
        _, ids = upload_batch(client, aws_fakes, headers, [("a.md", TEXT, "text/markdown")])
        job = aws_fakes.sqs.sent[0]
        aws_fakes.bedrock.embed_error = RuntimeError("bedrock throttled")
        with pytest.raises(RuntimeError):
            worker.handler(event(job), None)

        aws_fakes.bedrock.embed_error = None
        worker.handler(event(job), None)

        status, error, chunks = file_state(db, ids[0])
        assert (status, error) == (FileStatus.processed, None)
        assert chunks >= 1

    def test_a_failure_part_way_through_embedding_leaves_no_partial_chunks(
        self, client, db, aws_fakes, headers, production, monkeypatch
    ):
        long_text = ("Sentence number %d is here. " * 200) % tuple(range(200))
        _, ids = upload_batch(client, aws_fakes, headers, [("a.txt", long_text.encode(), "text/plain")])
        original = aws_fakes.bedrock.invoke_model
        calls = {"n": 0}

        def flaky(**kwargs):
            calls["n"] += 1
            if calls["n"] == 2:
                raise RuntimeError("boom")
            return original(**kwargs)

        monkeypatch.setattr(aws_fakes.bedrock, "invoke_model", flaky)

        with pytest.raises(RuntimeError):
            worker.handler(event(*aws_fakes.sqs.sent), None)

        assert calls["n"] == 2
        assert file_state(db, ids[0])[2] == 0

    def test_a_batch_fails_as_a_whole_but_redelivery_does_not_redo_finished_files(
        self, client, db, aws_fakes, headers, production
    ):
        _, ids = upload_batch(
            client,
            aws_fakes,
            headers,
            [("a.txt", b"first file words", "text/plain"), ("b.txt", b"second file words", "text/plain")],
        )
        first, second = aws_fakes.sqs.sent
        original = aws_fakes.bedrock.invoke_model

        def fail_for_second(**kwargs):
            if "second" in json.loads(kwargs["body"])["inputText"]:
                raise RuntimeError("boom")
            return original(**kwargs)

        aws_fakes.bedrock.invoke_model = fail_for_second
        with pytest.raises(RuntimeError):
            worker.handler(event(first, second), None)
        assert file_state(db, ids[0])[0] == FileStatus.processed
        assert file_state(db, ids[1])[0] == FileStatus.error

        aws_fakes.bedrock.invoke_model = original
        embeds_before = aws_fakes.bedrock.embed_calls
        worker.handler(event(first, second), None)

        assert [file_state(db, i) for i in ids] == [(FileStatus.processed, None, 1)] * 2
        assert aws_fakes.bedrock.embed_calls == embeds_before + 1  # only the failed file

    def test_a_file_deleted_before_processing_fails_the_message(
        self, client, db, aws_fakes, headers, production
    ):
        _, ids = upload_batch(client, aws_fakes, headers, [("a.md", TEXT, "text/markdown")])
        job = aws_fakes.sqs.sent[0]
        assert client.delete(f"/api/files/{ids[0]}", headers=headers).status_code in (200, 204)
        aws_fakes.s3.put(job["storage_key"], TEXT)  # object still in the bucket when the worker runs

        with pytest.raises(FileNotFoundError):
            worker.handler(event(job), None)

    @pytest.mark.parametrize(
        "record",
        [{"body": "not json"}, {"body": "{}"}, {"body": json.dumps({"file_id": 1})}, {}],
        ids=["malformed-json", "empty-job", "missing-fields", "no-body"],
    )
    def test_malformed_messages_raise_so_they_reach_the_dead_letter_queue(self, record, flushes):
        with pytest.raises((ValueError, KeyError)):
            worker.handler({"Records": [record]}, None)
        assert flushes == [1]

    def test_an_empty_event_does_nothing(self, flushes):
        worker.handler({"Records": []}, None)
        assert flushes == []

    def test_an_empty_file_is_processed_with_no_chunks_instead_of_failing(
        self, client, db, aws_fakes, headers, production
    ):
        _, ids = upload_batch(client, aws_fakes, headers, [("empty.txt", b"   ", "text/plain")])

        worker.handler(event(*aws_fakes.sqs.sent), None)

        assert file_state(db, ids[0]) == (FileStatus.processed, None, 0)


class TestLocalProcessing:
    """Outside production the web process does the work in a background task."""

    def test_upload_is_processed_inline_and_named(self, client, db, aws_fakes, headers):
        aws_fakes.bedrock.answer = "Local Notes"
        project_id, file_id, _ = upload_and_confirm(
            client, aws_fakes, headers, "a.md", TEXT, "text/markdown"
        )

        assert file_state(db, file_id)[0] == FileStatus.processed
        assert aws_fakes.sqs.sent == []
        assert db.get(Project, project_id).name == "Local Notes"
