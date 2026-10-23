import io
import subprocess
import zipfile
from types import SimpleNamespace

import pymupdf
import pytest
from docx import Document
from docx.enum.style import WD_STYLE_TYPE

from src.exceptions import ProcessingLimitError
from src.features.files import file_extraction_service as extraction
from src.features.files.file_extraction_service import (
    clean_text,
    extract_csv,
    extract_doc,
    extract_docx,
    extract_file,
    extract_pdf,
    extract_text,
)
from src.settings import settings

pytestmark = pytest.mark.unit

DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def make_pdf(pages: list[str]) -> bytes:
    document = pymupdf.open()
    for text in pages:
        page = document.new_page()
        if text:
            page.insert_text((72, 100), text)
    return document.tobytes()


def make_docx(build) -> bytes:
    document = Document()
    build(document)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


class TestPlainTextAndMarkdown:
    def test_utf8_is_decoded(self):
        assert extract_text("café ☕".encode()) == "café ☕"

    def test_utf8_bom_is_stripped(self):
        assert extract_text(b"\xef\xbb\xbfhello") == "hello"

    def test_legacy_cp1252_falls_back_instead_of_failing(self):
        assert extract_text("café".encode("cp1252")) == "café"

    def test_empty_file_gives_empty_text(self):
        assert extract_text(b"") == ""

    def test_markdown_is_passed_through_unchanged(self):
        source = "# Title\n\n- item one\n- item two\n"
        assert extract_file(source.encode(), "text/markdown") == source


class TestCsv:
    def test_rows_become_pipe_separated_lines(self):
        text = extract_csv(b"name,role\nAda,engineer\nBo,designer\n")
        assert text == "name | role\n\nAda | engineer\n\nBo | designer"

    def test_quoted_commas_and_newlines_stay_in_one_cell(self):
        text = extract_csv(b'name,note\nAda,"likes tea, and\ncoffee"\n')
        assert "Ada | likes tea, and\ncoffee" in text

    def test_blank_rows_and_cell_whitespace_are_dropped(self):
        text = extract_csv(b"a , b\n,\n\n  c ,d\n")
        assert text == "a | b\n\nc | d"

    def test_ragged_rows_are_kept(self):
        assert extract_csv(b"a,b,c\nd\n") == "a | b | c\n\nd"

    def test_unicode_and_cp1252(self):
        assert extract_csv("name\nZoë\n".encode("cp1252")) == "name\n\nZoë"

    def test_empty_csv(self):
        assert extract_csv(b"") == ""


class TestPdf:
    def test_text_from_every_page_is_extracted(self):
        text = extract_pdf(make_pdf(["Alpha page content", "Beta page content"]))
        assert "Alpha page content" in text
        assert "Beta page content" in text

    def test_pdf_without_text_gives_empty_string(self):
        assert extract_pdf(make_pdf([""])).strip() == ""

    def test_corrupt_pdf_raises(self):
        with pytest.raises(pymupdf.FileDataError):
            extract_pdf(b"%PDF-1.4 definitely not a pdf")

    def test_page_limit_is_enforced(self, monkeypatch):
        monkeypatch.setattr(settings, "MAX_PDF_PAGES", 2)
        with pytest.raises(ProcessingLimitError, match="more than 2 pages"):
            extract_pdf(make_pdf(["a", "b", "c"]))

    def test_clean_text_joins_hyphen_free_line_breaks_and_collapses_whitespace(self):
        assert clean_text("inter\nnational   trade\t\tpolicy") == "international trade policy"
        assert clean_text("one\n\n\n\n\ntwo") == "one\n\ntwo"
        assert clean_text("  padded  ") == "padded"


class TestDocx:
    def test_headings_become_markdown_headings(self):
        def build(doc):
            doc.add_heading("Overview", level=1)
            doc.add_paragraph("Intro text.")
            doc.add_heading("Details", level=2)
            doc.add_paragraph("More text.")

        text = extract_docx(make_docx(build))
        assert text == "# Overview\n\nIntro text.\n\n## Details\n\nMore text."

    def test_empty_paragraphs_are_skipped(self):
        def build(doc):
            doc.add_paragraph("   ")
            doc.add_paragraph("Real content")

        assert extract_docx(make_docx(build)) == "Real content"

    def test_tables_are_included_as_pipe_rows(self):
        def build(doc):
            table = doc.add_table(rows=2, cols=2)
            for r, row in enumerate([["Item", "Price"], ["Tea", "3"]]):
                for c, value in enumerate(row):
                    table.cell(r, c).text = value

        text = extract_docx(make_docx(build))
        assert "Item | Price" in text
        assert "Tea | 3" in text

    def test_empty_document_gives_empty_text(self):
        assert extract_docx(make_docx(lambda doc: None)) == ""

    def test_corrupt_docx_raises(self):
        with pytest.raises(zipfile.BadZipFile):
            extract_docx(b"PK\x03\x04 not really a docx")

    @pytest.mark.xfail(
        strict=True,
        raises=ValueError,
        reason="Known bug: a paragraph style named 'Heading <word>' makes int() fail "
        "in extract_docx, so the whole file errors instead of being treated as plain text",
    )
    def test_non_numeric_heading_style_does_not_break_extraction(self):
        def build(doc):
            doc.styles.add_style("Heading Note", WD_STYLE_TYPE.PARAGRAPH)
            doc.add_paragraph("A custom styled paragraph", style="Heading Note")

        assert "A custom styled paragraph" in extract_docx(make_docx(build))


class TestDoc:
    def test_antiword_output_is_decoded(self, monkeypatch):
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append((cmd, kwargs))
            return SimpleNamespace(stdout="  Legacy café text \n".encode("cp1252"))

        monkeypatch.setattr(extraction.subprocess, "run", fake_run)

        assert extract_doc(b"binary-doc") == "Legacy café text"
        cmd, kwargs = calls[0]
        assert cmd == ["antiword", "-"]
        assert kwargs["input"] == b"binary-doc"
        assert kwargs["timeout"] == 30

    @pytest.mark.parametrize(
        "error",
        [
            subprocess.CalledProcessError(1, "antiword"),
            subprocess.TimeoutExpired("antiword", 30),
            FileNotFoundError("antiword"),
        ],
        ids=["non-zero-exit", "timeout", "antiword-missing"],
    )
    def test_antiword_failures_propagate_so_the_file_is_marked_as_error(
        self, monkeypatch, error
    ):
        def failing_run(*args, **kwargs):
            raise error

        monkeypatch.setattr(extraction.subprocess, "run", failing_run)

        with pytest.raises(type(error)):
            extract_doc(b"binary-doc")


class TestExtractFile:
    def test_every_supported_mime_type_has_an_extractor(self):
        assert set(extraction.EXTRACTION_METHODS) == {
            "text/plain",
            "text/markdown",
            "text/csv",
            "application/pdf",
            DOCX,
            "application/msword",
        }

    @pytest.mark.parametrize(
        "mime_type", ["image/png", "application/zip", "application/json", "", "TEXT/PLAIN"]
    )
    def test_unsupported_types_are_rejected(self, mime_type):
        with pytest.raises(ValueError, match="Unsupported file type"):
            extract_file(b"data", mime_type)

    def test_dispatches_by_mime_type(self):
        assert extract_file(b"a,b\n1,2", "text/csv") == "a | b\n\n1 | 2"
        assert extract_file(b"a,b\n1,2", "text/plain") == "a,b\n1,2"

    def test_text_over_the_character_limit_is_rejected(self, monkeypatch):
        monkeypatch.setattr(settings, "MAX_EXTRACTED_CHARS", 10)
        with pytest.raises(ProcessingLimitError, match="too much text"):
            extract_file(b"x" * 11, "text/plain")

    def test_text_exactly_at_the_limit_is_accepted(self, monkeypatch):
        monkeypatch.setattr(settings, "MAX_EXTRACTED_CHARS", 10)
        assert extract_file(b"x" * 10, "text/plain") == "x" * 10

    def test_empty_files_extract_to_empty_text(self):
        # Callers (chunking) must therefore cope with empty text; see test_chunking.
        assert extract_file(b"", "text/plain") == ""
