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
    ],
)
def test_mismatched_extension_rejected(name, mime):
    with pytest.raises(ValueError):
        FileCreate(name=name, mime_type=mime, size=10)


def test_path_is_stripped_and_long_names_rejected():
    assert FileCreate(name="C:\\Users\\me\\a.txt", mime_type="text/plain", size=1).name == "a.txt"
    assert FileCreate(name="../../etc/a.txt", mime_type="text/plain", size=1).name == "a.txt"
    with pytest.raises(ValueError):
        FileCreate(name="x" * 300 + ".txt", mime_type="text/plain", size=1)


def test_unknown_mime_message_lists_extensions():
    with pytest.raises(ValueError) as caught:
        FileCreate(name="a.png", mime_type="image/png", size=1)
    assert ".docx" in str(caught.value) and ".doc" in str(caught.value)


def test_upload_endpoint_rejects_mismatch(client, make_user):
    _, headers = make_user()
    body = [{"name": "report.pdf", "mimeType": "text/csv", "size": 5}]
    assert client.post("/api/files", json=body, headers=headers).status_code == 422
