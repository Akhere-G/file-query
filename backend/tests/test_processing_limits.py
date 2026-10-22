import random
import time

import pymupdf
import pytest

from src.features.files import file_processing_service as processing
from src.settings import settings
from tests.helpers import upload_and_confirm


def state(client, headers, project_id):
    return client.get(f"/api/projects/{project_id}/files", headers=headers).json()[0]


def test_too_many_files_in_one_request(client, make_user):
    _, headers = make_user()
    body = [{"name": f"{i}.txt", "mimeType": "text/plain", "size": 5} for i in range(11)]
    res = client.post("/api/files", json=body, headers=headers)
    assert res.status_code == 400


def test_oversize_file_rejected_at_upload(client, make_user):
    _, headers = make_user()
    body = [{"name": "a.txt", "mimeType": "text/plain", "size": settings.MAX_FILE_SIZE}]
    assert client.post("/api/files", json=body, headers=headers).status_code == 422


def test_chunk_cap_stops_processing_before_any_bedrock_call(
    client, make_user, aws_fakes, monkeypatch
):
    monkeypatch.setattr(settings, "MAX_CHUNKS_PER_FILE", 3)
    _, headers = make_user()
    text = (" ".join(f"word{i}" for i in range(3000))).encode()
    project_id, _, _ = upload_and_confirm(client, aws_fakes, headers, "big.txt", text)
    file = state(client, headers, project_id)
    assert file["status"] == "error"
    assert "too large" in file["error"]
    assert aws_fakes.bedrock.embed_calls == 0


def test_text_cap(client, make_user, aws_fakes, monkeypatch):
    monkeypatch.setattr(settings, "MAX_EXTRACTED_CHARS", 100)
    _, headers = make_user()
    project_id, _, _ = upload_and_confirm(client, aws_fakes, headers, "a.txt", b"x" * 500)
    file = state(client, headers, project_id)
    assert file["status"] == "error" and "too much text" in file["error"]


def test_pdf_page_cap(client, make_user, aws_fakes, monkeypatch):
    monkeypatch.setattr(settings, "MAX_PDF_PAGES", 2)
    doc = pymupdf.open()
    for _ in range(3):
        doc.new_page().insert_text((72, 72), "hello")
    _, headers = make_user()
    project_id, _, _ = upload_and_confirm(
        client, aws_fakes, headers, "long.pdf", doc.tobytes(), mime="application/pdf"
    )
    file = state(client, headers, project_id)
    assert file["status"] == "error" and "pages" in file["error"]


def test_normal_file_is_embedded_without_per_chunk_llm_calls(client, make_user, aws_fakes):
    _, headers = make_user()
    text = ("Bananas are yellow. " * 400).encode()
    project_id, _, _ = upload_and_confirm(client, aws_fakes, headers, "a.txt", text)
    assert state(client, headers, project_id)["status"] == "processed"
    assert aws_fakes.bedrock.embed_calls > 1
    # at most the single project-naming call, never one per chunk
    assert aws_fakes.bedrock.converse_calls <= 1


@pytest.mark.parametrize(
    "content, expected",
    [
        ("# Setup\nInstall the thing.", "Setup"),
        ("Intro text.\n## Usage guide\nMore", "Usage guide"),
        ("First sentence here. Second one follows.", "First sentence here."),
        ("**Bold** start without punctuation", "Bold start without punctuation"),
        ("   \n  ", None),
    ],
)
def test_derive_chunk_title(content, expected):
    assert processing.derive_chunk_title(content) == expected


def test_title_is_at_most_100_characters():
    assert len(processing.derive_chunk_title("a" * 500)) == 100


def test_embeddings_keep_input_order_under_concurrency(monkeypatch):
    def slow_embedding(text):
        time.sleep(random.random() * 0.01)
        return [float(text.split("-")[1])] + [0.0] * 1023

    monkeypatch.setattr(processing, "generate_embedding", slow_embedding)
    contents = [f"chunk-{i}" for i in range(40)]
    chunks = processing.create_chunks(1, contents)
    assert [c.content for c in chunks] == contents
    assert [c.embedding[0] for c in chunks] == [float(i) for i in range(40)]
