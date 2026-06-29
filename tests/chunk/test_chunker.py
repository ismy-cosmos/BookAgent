import pytest
from pipeline.chunk import Chunk, Chunker
from pipeline.parse.base import Element


def _el(content: str, etype: str = "text", page_num: int = 1) -> Element:
    return Element(type=etype, content=content, page_num=page_num)


def test_empty_elements_returns_empty():
    c = Chunker()
    assert c.chunk([], book_id="b", source_file="f.pdf") == []


def test_single_short_element_becomes_one_chunk():
    c = Chunker()
    elems = [_el("This is a short paragraph.")]
    chunks = c.chunk(elems, book_id="b", source_file="ch01.pdf")
    assert len(chunks) == 1
    assert chunks[0].book_id == "b"
    assert chunks[0].source_file == "ch01.pdf"
    assert chunks[0].page_start == 1
    assert "short paragraph" in chunks[0].content
    assert chunks[0].chunk_id == "b/ch01/p0001/0000"


def test_heading_splits_into_separate_chunks():
    c = Chunker()
    elems = [
        _el("First section text."),
        _el("## New Section", "text", 1),
        _el("Second section text."),
    ]
    chunks = c.chunk(elems, book_id="b", source_file="f.pdf")
    assert len(chunks) == 2
    assert "## New Section" not in chunks[0].content
    assert "## New Section" not in chunks[1].content
    assert "First section" in chunks[0].content
    assert "Second section" in chunks[1].content


def test_heading_flush_has_no_overlap():
    c = Chunker(overlap_tokens=10)
    elems = [
        _el("A " * 30),       # ~30 tokens
        _el("## Cut", "text"),
        _el("B " * 5),
    ]
    chunks = c.chunk(elems, book_id="b", source_file="f.pdf")
    assert len(chunks) == 2
    # second chunk must NOT contain words from first chunk (no overlap after heading)
    assert "A A A" not in chunks[1].content


def test_atomic_element_emitted_alone():
    c = Chunker()
    elems = [
        _el("Intro text."),
        _el("| A | B |\n|---|---|\n| 1 | 2 |", "table"),
        _el("Outro text."),
    ]
    chunks = c.chunk(elems, book_id="b", source_file="f.pdf")
    assert len(chunks) == 3
    table_chunk = next(ch for ch in chunks if ch.element_type == "table")
    assert "| A | B |" in table_chunk.content


def test_section_break_element_flushes_without_overlap():
    c = Chunker(overlap_tokens=10)
    elems = [
        _el("A " * 20),
        Element(type="section_break", content="", page_num=0),
        _el("B " * 5),
    ]
    chunks = c.chunk(elems, book_id="b", source_file="f.pdf")
    assert len(chunks) == 2
    assert "A A A" not in chunks[1].content


def test_page_num_zero_gives_none_page_start():
    c = Chunker()
    elems = [_el("Some content.", page_num=0)]
    chunks = c.chunk(elems, book_id="b", source_file="f.epub")
    assert chunks[0].page_start is None
    assert "/pNone/" in chunks[0].chunk_id


def test_token_count_is_set():
    c = Chunker()
    elems = [_el("hello world foo bar")]
    chunks = c.chunk(elems, book_id="b", source_file="f.pdf")
    assert chunks[0].token_count > 0


def test_seq_offset():
    c = Chunker()
    elems = [_el("text")]
    chunks = c.chunk(elems, book_id="b", source_file="f.pdf", seq_offset=5)
    assert chunks[0].chunk_id.endswith("/0005")


def test_overlap_carries_into_next_chunk():
    # Use a tiny overlap to verify it happens
    c = Chunker(max_tokens=10, overlap_tokens=3)
    # Build elements that will each flush (each ~10 tokens)
    elems = [
        _el("alpha beta gamma delta epsilon zeta eta theta"),  # ~8 tokens
        _el("iota kappa lambda mu nu xi omicron pi"),          # ~8 tokens
    ]
    chunks = c.chunk(elems, book_id="b", source_file="f.pdf")
    # second chunk should start with overlap from first
    assert len(chunks) == 2
    # overlap tokens should appear at start of chunk[1] content
    first_words = chunks[0].content.split()[-3:]
    assert any(w in chunks[1].content for w in first_words)
