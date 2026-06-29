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
    # Each element fits individually (<= 10 tokens), but together they exceed 10
    elems = [
        _el("alpha beta gamma delta epsilon zeta eta theta"),  # 9 tokens
        _el("iota kappa lambda mu nu xi omicron"),             # 10 tokens
    ]
    chunks = c.chunk(elems, book_id="b", source_file="f.pdf")
    # second chunk should start with overlap from first
    assert len(chunks) == 2
    # overlap tokens should appear at start of chunk[1] content
    first_words = chunks[0].content.split()[-3:]
    assert any(w in chunks[1].content for w in first_words)


def test_split_at_sentence_chinese():
    c = Chunker(max_tokens=5)
    # 中文句子用。分隔，无空格
    elems = [_el("你好世界。这是第二句。这是第三句。", page_num=1)]
    chunks = c.chunk(elems, book_id="b", source_file="f.pdf")
    assert len(chunks) >= 2  # 应被分割


def test_long_element_pieces_carry_overlap():
    c = Chunker(max_tokens=15, overlap_tokens=5)
    # 单个元素超出 max_tokens，会被切成多片
    long_text = (
        "First complete sentence ends here. "
        "Second complete sentence ends here. "
        "Third complete sentence ends here."
    )
    elems = [_el(long_text, page_num=1)]
    chunks = c.chunk(elems, book_id="b", source_file="f.pdf")
    assert len(chunks) >= 2
    # 后续切片的内容应含有前一片末尾的词（overlap）
    for i in range(1, len(chunks)):
        prev_words = set(chunks[i-1].content.split())
        curr_words = set(chunks[i].content.split())
        assert prev_words & curr_words, f"chunk {i} has no overlap with chunk {i-1}"
