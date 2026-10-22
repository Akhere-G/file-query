import pytest

from src.features.files.file_schema import FileCreate

DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@pytest.mark.parametrize(
    "name, mime",
    [
        ("notes.md", "text/markdown"),
        ("README.MARKDOWN", "text/markdown"),
        ("data.csv", "text/csv"),
        ("report.PDF", "application/pdf"),
        ("letter.doc", "application/msword"),
        ("letter.docx", DOCX),
        ("a.txt", "text/plain"),
    ],
)
def test_matching_extension_and_type_accepted(name, mime):
    assert FileCreate(name=name, mime_type=mime, size=10).name == name


@pytest.mark.parametrize(
    "name, mime",
    [
        ("report.pdf", "text/csv"),
        ("letter.docx", "application/msword"),
        ("noextension", "text/plain"),
        ("a.exe", "application/pdf"),
        ("x" * 300 + ".txt", "text/plain"),
    ],
)
def test_mismatched_or_long_names_rejected(name, mime):
    with pytest.raises(ValueError):
        FileCreate(name=name, mime_type=mime, size=10)


def test_unknown_type_lists_the_supported_extensions():
    with pytest.raises(ValueError) as error:
        FileCreate(name="a.png", mime_type="image/png", size=1)
    assert ".docx" in str(error.value)


def test_upload_rejects_mismatch(client, make_user):
    _, headers = make_user()
    body = [{"name": "report.pdf", "mimeType": "text/csv", "size": 5}]
    assert client.post("/api/files", json=body, headers=headers).status_code == 422
