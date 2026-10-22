import subprocess

import pytest

from src.exceptions import ProcessingLimitError
from src.features.files import file_extraction_service as extraction

DOC = "application/msword"


def test_doc_text_is_extracted(monkeypatch):
    def fake_run(cmd, **kwargs):
        assert cmd == ["antiword", "-"] and kwargs["timeout"] == 30
        return subprocess.CompletedProcess(cmd, 0, stdout="Hello from Word\n".encode("cp1252"))

    monkeypatch.setattr(extraction.subprocess, "run", fake_run)
    assert extraction.extract_file(b"binary", DOC) == "Hello from Word"


@pytest.mark.parametrize(
    "error",
    [
        subprocess.CalledProcessError(1, "antiword"),
        subprocess.TimeoutExpired("antiword", 30),
        FileNotFoundError("antiword"),
    ],
)
def test_doc_failures_become_user_safe_errors(monkeypatch, error):
    def fake_run(cmd, **kwargs):
        raise error

    monkeypatch.setattr(extraction.subprocess, "run", fake_run)
    with pytest.raises(ProcessingLimitError) as caught:
        extraction.extract_file(b"garbage", DOC)
    assert ".docx" in caught.value.message
