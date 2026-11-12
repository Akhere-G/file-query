from itertools import pairwise

import pytest

from src.features.files.file_processing_service import (
    chunk_file,
    chunk_markdown,
    chunk_text,
    mime_types,
)

pytestmark = pytest.mark.unit

SENTENCE = "Lighthouses guide ships safely past dangerous rocks. "


def long_text(sentences: int) -> str:
    return "".join(f"{i}. {SENTENCE}" for i in range(sentences))


def test_short_text_is_a_single_chunk():
    assert chunk_text("A short note.") == ["A short note."]


@pytest.mark.parametrize("text", ["", "   \n\n  "])
def test_empty_or_blank_text_produces_no_chunks(text):
    assert chunk_text(text) == []


def test_chunks_never_exceed_the_configured_size():
    chunks = chunk_text(long_text(200))
    assert len(chunks) > 1
    assert all(len(chunk) <= 1500 for chunk in chunks)


def test_no_chunk_is_empty():
    assert all(chunk.strip() for chunk in chunk_text(long_text(200)))


def test_consecutive_chunks_overlap_so_context_is_not_lost_at_boundaries():
    chunks = chunk_text(long_text(200))
    for previous, following in pairwise(chunks):
        assert following[:30] in previous


def test_all_content_is_preserved_across_chunks():
    text = long_text(120)
    joined = " ".join(chunk_text(text))
    for i in (0, 60, 119):
        assert f"{i}. Lighthouses" in joined


def test_custom_chunk_size_and_overlap_are_respected():
    chunks = chunk_text("word " * 100, chunk_size=50, chunk_overlap=10)
    assert len(chunks) > 5
    assert all(len(chunk) <= 50 for chunk in chunks)


def test_unicode_text_is_not_corrupted():
    text = "Zoë café 日本語 ☕ " * 300
    chunks = chunk_text(text)
    assert all("�" not in chunk for chunk in chunks)
    assert "日本語" in chunks[0]


def test_a_single_very_long_token_is_still_split():
    chunks = chunk_text("x" * 4000)
    assert len(chunks) >= 3
    assert all(len(chunk) <= 1500 for chunk in chunks)


class TestMarkdownChunking:
    def test_each_heading_section_is_chunked_separately_and_keeps_its_heading(self):
        text = "# Cats\n\nCats purr.\n\n## Diet\n\nCats eat fish.\n\n# Dogs\n\nDogs bark."
        chunks = chunk_markdown(text)
        assert len(chunks) == 3
        assert chunks[0].startswith("# Cats")
        assert any("## Diet" in chunk and "fish" in chunk for chunk in chunks)
        assert chunks[-1].startswith("# Dogs")

    def test_long_sections_are_split_to_the_size_limit(self):
        chunks = chunk_markdown("# Title\n\n" + long_text(200))
        assert len(chunks) > 1
        assert all(len(chunk) <= 1500 for chunk in chunks)

    def test_chunk_file_dispatches_by_mime_type(self):
        text = "# One\n\nfirst\n\n# Two\n\nsecond"
        assert chunk_file(text, "application/pdf") == chunk_markdown(text)
        assert chunk_file(text, "text/plain") == chunk_text(text)
        assert chunk_file(text, "something/unknown") == chunk_text(text)

    def test_every_supported_mime_type_has_a_split_strategy(self):
        assert set(mime_types) == {
            "application/msword",
            "text/plain",
            "text/csv",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/pdf",
            "text/markdown",
        }
