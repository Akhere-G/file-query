import pymupdf
import pytest

from src.features.files.file_processing_service import derive_chunk_title
from src.settings import settings
from tests.helpers import upload_and_confirm


def first_file(client, headers, project_id):
    return client.get(f"/api/projects/{project_id}/files", headers=headers).json()[0]


def test_too_many_files_in_one_request(client, make_user):
    _, headers = make_user()
    body = [{"name": f"{i}.txt", "mimeType": "text/plain", "size": 5} for i in range(11)]
    assert client.post("/api/files", json=body, headers=headers).status_code == 400


def test_oversize_file_rejected_at_upload(client, make_user):
    _, headers = make_user()
    body = [{"name": "a.txt", "mimeType": "text/plain", "size": settings.MAX_FILE_SIZE}]
    assert client.post("/api/files", json=body, headers=headers).status_code == 422


def test_chunk_cap_stops_processing_before_any_embedding(client, make_user, aws_fakes, monkeypatch):
    monkeypatch.setattr(settings, "MAX_CHUNKS_PER_FILE", 3)
    _, headers = make_user()
    text = " ".join(f"word{i}" for i in range(3000)).encode()
    project_id, _, _ = upload_and_confirm(client, aws_fakes, headers, "big.txt", text)
    file = first_file(client, headers, project_id)
    assert file["status"] == "error"
    assert "too large" in file["error"]
    assert aws_fakes.bedrock.embed_calls == 0


def test_text_cap(client, make_user, aws_fakes, monkeypatch):
    monkeypatch.setattr(settings, "MAX_EXTRACTED_CHARS", 100)
    _, headers = make_user()
    project_id, _, _ = upload_and_confirm(client, aws_fakes, headers, "a.txt", b"x" * 500)
    file = first_file(client, headers, project_id)
    assert file["status"] == "error"
    assert "too much text" in file["error"]


def test_pdf_page_cap(client, make_user, aws_fakes, monkeypatch):
    monkeypatch.setattr(settings, "MAX_PDF_PAGES", 2)
    document = pymupdf.open()
    for _ in range(3):
        document.new_page().insert_text((72, 72), "hello")
    _, headers = make_user()
    project_id, _, _ = upload_and_confirm(
        client, aws_fakes, headers, "long.pdf", document.tobytes(), "application/pdf"
    )
    file = first_file(client, headers, project_id)
    assert file["status"] == "error"
    assert "pages" in file["error"]


def test_chunks_are_embedded_without_a_title_call_per_chunk(client, make_user, aws_fakes):
    _, headers = make_user()
    text = ("Bananas are yellow. " * 400).encode()
    project_id, _, _ = upload_and_confirm(client, aws_fakes, headers, "a.txt", text)
    assert first_file(client, headers, project_id)["status"] == "processed"
    assert aws_fakes.bedrock.embed_calls > 1
    assert aws_fakes.bedrock.converse_calls <= 1


@pytest.mark.parametrize(
    "content, expected",
    [
        ("# Setup\nInstall the thing.", "Setup"),
        ("Intro text.\n## Usage guide\nMore", "Usage guide"),
        ("First sentence here. Second one follows.", "First sentence here."),
        ("**Bold** start without punctuation", "Bold start without punctuation"),
        ("   \n  ", None),
        ("a" * 500, "a" * 100),
    ],
)
def test_derive_chunk_title(content, expected):
    assert derive_chunk_title(content) == expected
