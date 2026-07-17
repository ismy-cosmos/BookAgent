import pytest
from pipeline.chunk import Chunk, Chunker
from pipeline.parse.base import Element
from pipeline.chunk.chunker import _split_at_sentence, _token_count


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
    assert chunks[0].page_end == 1
    assert "short paragraph" in chunks[0].content
    assert chunks[0].chunk_id == "b/ch01.pdf/p0001/0000"


def test_page_end_reflects_last_element_when_chunk_spans_pages():
    """A buffer with no heading/atomic boundary in between can span pages —
    page_end must reflect that, not silently report page_start's value."""
    c = Chunker()
    elems = [
        _el("Page five content.", page_num=5),
        _el("Page six content, same chunk.", page_num=6),
    ]
    chunks = c.chunk(elems, book_id="b", source_file="f.pdf")
    assert len(chunks) == 1
    assert chunks[0].page_start == 5
    assert chunks[0].page_end == 6


def test_page_end_spans_three_pages():
    c = Chunker()
    elems = [
        _el("p7", page_num=7),
        _el("p8", page_num=8),
        _el("p9", page_num=9),
    ]
    chunks = c.chunk(elems, book_id="b", source_file="f.pdf")
    assert len(chunks) == 1
    assert chunks[0].page_start == 7
    assert chunks[0].page_end == 9


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
    assert chunks[0].page_end is None
    assert "/pNone/" in chunks[0].chunk_id


def test_atomic_element_page_start_equals_page_end():
    c = Chunker()
    elems = [_el("| A | B |\n|---|---|\n| 1 | 2 |", "table", page_num=4)]
    chunks = c.chunk(elems, book_id="b", source_file="f.pdf")
    assert chunks[0].page_start == 4
    assert chunks[0].page_end == 4


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


def test_buffer_overflow_does_not_carry_overlap():
    """Buffer overflow flush must NOT carry any overlap into the next chunk.

    Before this fix: the tail of chunk[0] was prepended to chunk[1].
    After this fix: chunk[1] contains only its own element's content.
    """
    c = Chunker(max_tokens=10, overlap_tokens=3)
    elems = [
        _el("alpha beta gamma delta epsilon zeta eta theta"),
        _el("iota kappa lambda mu nu xi omicron"),
    ]
    chunks = c.chunk(elems, book_id="b", source_file="f.pdf")
    assert len(chunks) == 2
    first_words = chunks[0].content.split()[-3:]
    assert not any(w in chunks[1].content for w in first_words)


def test_split_at_sentence_chinese():
    c = Chunker(max_tokens=5)
    # 中文句子用。分隔，无空格
    elems = [_el("你好世界。这是第二句。这是第三句。", page_num=1)]
    chunks = c.chunk(elems, book_id="b", source_file="f.pdf")
    assert len(chunks) >= 2  # 应被分割


def test_split_at_sentence_packs_short_sentences():
    """Multiple short sentences must be packed greedily into fewer pieces.

    Regression: commit 722980c dropped the buf/buf_tok accumulation, causing
    each sentence to become its own piece — a 533-token block splintered into
    32 tiny fragments in real data.
    """
    sentences = [
        "Alpha beta gamma delta epsilon.",
        "Zeta eta theta iota kappa.",
        "Lambda mu nu xi omicron.",
        "Pi rho sigma tau upsilon.",
    ]
    text = " ".join(sentences)
    total_tok = _token_count(text)
    max_tok = total_tok // 2  # forces at least one split; packing → ~2 pieces

    pieces = _split_at_sentence(text, max_tok)

    assert len(pieces) < len(sentences), (
        f"Packing bug: {len(sentences)} sentences produced {len(pieces)} pieces — "
        f"should be packed into fewer chunks than there are sentences"
    )
    for p in pieces:
        assert _token_count(p) <= max_tok, f"Piece exceeds budget: {p!r}"


def test_split_at_sentence_no_false_break_at_abbreviation():
    """'e.g.' must not be treated as a sentence boundary.

    The regex (?<=[.!?])\\s+ misfires at 'e.g. ' because the period in 'g.'
    looks like a sentence end. Fix: add (?=[A-Z\\d]) lookahead so that
    'e.g. the' (lowercase continuation) is never a split point.
    """
    text = (
        "Common scheduling algorithms, e.g. the round-robin and FIFO policies, "
        "are used in most modern operating systems. "
        "Performance evaluation requires careful benchmarking methodology."
    )
    max_tok = _token_count(text) // 2  # forces a split somewhere

    pieces = _split_at_sentence(text, max_tok)

    for piece in pieces:
        assert not piece.strip().startswith("the round-robin"), (
            f"False split at 'e.g.': piece starts mid-abbreviation: {piece.strip()!r}"
        )


def test_atomic_prefix_from_colon_ending_sentence():
    """Last sentence of the preceding text chunk, if it ends with ':', is
    prepended to the atomic chunk. Only the last sentence is used."""
    c = Chunker()
    elems = [
        _el("Some intro text. The schedule is as follows:"),
        _el("| T | Process |\n|---|---|\n| 0 | A |", "table"),
    ]
    chunks = c.chunk(elems, book_id="b", source_file="f.pdf")
    table_chunk = next(ch for ch in chunks if ch.element_type == "table")
    assert "The schedule is as follows:" in table_chunk.content
    assert "Some intro text" not in table_chunk.content


def test_atomic_prefix_removed_from_preceding_chunk_when_it_has_more_content():
    """The colon sentence copied into the atomic chunk must not also survive
    verbatim in the preceding text chunk it was pulled from — real corpus data
    (issue found via chunk-size audit) showed it duplicated in both places."""
    c = Chunker()
    elems = [
        _el("Some intro text. The schedule is as follows:"),
        _el("| T | Process |\n|---|---|\n| 0 | A |", "table"),
    ]
    chunks = c.chunk(elems, book_id="b", source_file="f.pdf")
    text_chunk = next(ch for ch in chunks if ch.element_type == "text")
    assert "Some intro text" in text_chunk.content
    assert "The schedule is as follows:" not in text_chunk.content
    assert text_chunk.token_count == _token_count(text_chunk.content)


def test_atomic_prefix_drops_preceding_chunk_when_fully_consumed():
    """If the preceding text chunk's *entire* content is the colon-ending lead-in
    sentence (common case: 'The code looks like this:' as its own element), the
    now-empty orphan chunk must be dropped from the output, not left in as a
    near-content-free duplicate of what's now prefixed onto the atomic chunk."""
    c = Chunker()
    elems = [
        _el("The associated signaling code would look like this:"),
        _el("ready = 1;", "code"),
    ]
    chunks = c.chunk(elems, book_id="b", source_file="f.pdf")
    assert len(chunks) == 1
    assert chunks[0].element_type == "code"
    assert "The associated signaling code would look like this:" in chunks[0].content
    assert "ready = 1;" in chunks[0].content


def test_atomic_no_prefix_when_last_sentence_lacks_colon():
    """No prefix when the preceding text's last sentence does not end with ':'."""
    c = Chunker()
    elems = [
        _el("This is context without a colon at the end."),
        _el("| A | B |\n|---|---|\n| 1 | 2 |", "table"),
    ]
    chunks = c.chunk(elems, book_id="b", source_file="f.pdf")
    table_chunk = next(ch for ch in chunks if ch.element_type == "table")
    assert "This is context" not in table_chunk.content


def test_atomic_no_prefix_after_heading():
    """When atomic immediately follows a heading (empty buffer), no prefix is added."""
    c = Chunker()
    elems = [
        _el("## Section Title", "text"),
        _el("```\ncode block\n```", "code"),
    ]
    chunks = c.chunk(elems, book_id="b", source_file="f.pdf")
    code_chunk = next(ch for ch in chunks if ch.element_type == "code")
    assert "Section Title" not in code_chunk.content


def test_atomic_no_prefix_when_preceding_chunk_is_atomic():
    """No prefix when chunks[-1].element_type is not 'text' (e.g. preceding table)."""
    c = Chunker()
    elems = [
        _el("| X |\n|---|\n| 1 |", "table"),
        _el("```\ncode\n```", "code"),
    ]
    chunks = c.chunk(elems, book_id="b", source_file="f.pdf")
    code_chunk = next(ch for ch in chunks if ch.element_type == "code")
    assert "X" not in code_chunk.content
    assert "1" not in code_chunk.content


def test_atomic_caption_consumed_not_emitted_separately():
    """A Figure/Table N.M: element immediately following an atomic is appended
    to the atomic chunk content and NOT emitted as a separate chunk."""
    c = Chunker()
    elems = [
        _el("![fig](_page_1_Figure_1.jpeg)", "figure"),
        _el("Figure 3.2: Process lifecycle diagram."),
    ]
    chunks = c.chunk(elems, book_id="b", source_file="f.pdf")
    assert len(chunks) == 1
    assert "Figure 3.2: Process lifecycle diagram." in chunks[0].content


def test_atomic_caption_consumed_when_chinese_caption():
    """中文书籍的"图 N-M　说明文字"格式（真实语料：java-ch1-e2e.epub，用全角空格
    做分隔，不带冒号）同样要被识别为caption并消费掉，不能只认英文Figure/Table。"""
    c = Chunker()
    elems = [
        _el("![fig](_page_1_Figure_1.jpeg)", "figure"),
        _el("图 1-5　两个线程对共享变量的访问顺序"),
    ]
    chunks = c.chunk(elems, book_id="b", source_file="f.epub")
    assert len(chunks) == 1
    assert "图 1-5　两个线程对共享变量的访问顺序" in chunks[0].content


def test_atomic_no_caption_for_inline_figure_reference():
    """"图1-5就展示了……"是正文里提到图号的引用句，不是caption行（真实语料区别：
    caption是"图 1-5"带空格，正文引用是"图1-5"紧挨着数字），不能被误吸收。"""
    c = Chunker()
    elems = [
        _el("![fig](_page_1_Figure_1.jpeg)", "figure"),
        _el("图1-5就展示了如果没有同步好，两个线程同时向共享变量写入的情况。"),
    ]
    chunks = c.chunk(elems, book_id="b", source_file="f.epub")
    assert len(chunks) == 2
    text_chunk = next(ch for ch in chunks if ch.element_type == "text")
    assert "图1-5就展示了" in text_chunk.content


def test_atomic_caption_page_end_extended_to_caption_page():
    """When caption is on the following page, page_end of atomic chunk reflects
    the caption's page number."""
    c = Chunker()
    elems = [
        _el("![fig](_page_1_Figure_1.jpeg)", "figure", page_num=3),
        _el("Figure 1.1: Caption on next page.", page_num=4),
    ]
    chunks = c.chunk(elems, book_id="b", source_file="f.pdf")
    assert len(chunks) == 1
    assert chunks[0].page_end == 4


def test_atomic_both_prefix_and_caption():
    """Prefix (colon sentence) and caption can both be present simultaneously."""
    c = Chunker()
    elems = [
        _el("The CPU schedule is as follows:"),
        _el("| T | Job |\n|---|---|\n| 0 | A |", "table"),
        _el("Table 3.1: A simple FIFO schedule."),
    ]
    chunks = c.chunk(elems, book_id="b", source_file="f.pdf")
    table_chunk = next(ch for ch in chunks if ch.element_type == "table")
    assert "The CPU schedule is as follows:" in table_chunk.content
    assert "Table 3.1: A simple FIFO schedule." in table_chunk.content


def test_atomic_next_element_not_caption_stays_separate():
    """A following text element that does NOT match Figure/Table N.M: pattern
    is emitted as a normal separate chunk, not consumed."""
    c = Chunker()
    elems = [
        _el("| A |\n|---|\n| 1 |", "table"),
        _el("This paragraph follows the table."),
    ]
    chunks = c.chunk(elems, book_id="b", source_file="f.pdf")
    assert len(chunks) == 2
    assert "This paragraph follows" in chunks[1].content


def test_atomic_as_last_element_no_error():
    """Atomic as the last element: no IndexError, correct single chunk output."""
    c = Chunker()
    elems = [
        _el("Some context."),
        _el("| A |\n|---|\n| 1 |", "table"),
    ]
    chunks = c.chunk(elems, book_id="b", source_file="f.pdf")
    assert len(chunks) == 2
    table_chunk = next(ch for ch in chunks if ch.element_type == "table")
    assert "A" in table_chunk.content


def test_long_element_first_piece_excludes_buffer_content():
    """When a long element is split, its first piece must not carry overlap
    from a preceding buffer flush — inter-piece overlap is kept but
    buffer-to-first-piece overlap is removed."""
    c = Chunker(max_tokens=8, overlap_tokens=3)
    long_text = "Alpha Beta Gamma Delta Epsilon. Zeta Eta Theta Iota Kappa."
    elems = [
        _el("unique preceding text"),
        _el(long_text),
    ]
    chunks = c.chunk(elems, book_id="b", source_file="f.pdf")
    assert chunks[0].content == "unique preceding text"
    assert "unique" not in chunks[1].content
    assert "preceding" not in chunks[1].content


def test_cross_page_table_continuation_merged():
    """Two consecutive table elements where first lacks separator and second
    starts with separator (cross-page split) are merged into one chunk.
    page_start from the first element, page_end from the second."""
    c = Chunker()
    elems = [
        _el("| A | B |\n|", "table", page_num=3),
        _el("----|----|\n| 1 | 2 |", "table", page_num=4),
    ]
    chunks = c.chunk(elems, book_id="b", source_file="f.pdf")
    assert len(chunks) == 1
    assert chunks[0].element_type == "table"
    assert "| A | B |" in chunks[0].content
    assert "| 1 | 2 |" in chunks[0].content
    assert chunks[0].page_start == 3
    assert chunks[0].page_end == 4


def test_two_complete_tables_not_merged():
    """Two consecutive tables that each have a separator row remain separate chunks."""
    c = Chunker()
    elems = [
        _el("| A | B |\n|---|---|\n| 1 | 2 |", "table", page_num=1),
        _el("| X | Y |\n|---|---|\n| 3 | 4 |", "table", page_num=2),
    ]
    chunks = c.chunk(elems, book_id="b", source_file="f.pdf")
    assert len(chunks) == 2
    assert "| A | B |" in chunks[0].content
    assert "| X | Y |" in chunks[1].content


def test_cross_page_table_continuation_with_caption():
    """Merged cross-page table also correctly consumes a trailing caption element."""
    c = Chunker()
    elems = [
        _el("| A | B |\n|", "table", page_num=3),
        _el("----|----|\n| 1 | 2 |", "table", page_num=4),
        _el("Table 2.1: Example results.", page_num=4),
    ]
    chunks = c.chunk(elems, book_id="b", source_file="f.pdf")
    assert len(chunks) == 1
    assert "Table 2.1: Example results." in chunks[0].content
    assert chunks[0].page_start == 3
    assert chunks[0].page_end == 4


def test_complete_first_table_not_merged_with_body():
    """If first table already has a separator row, no merge occurs even if
    second element looks like a continuation."""
    c = Chunker()
    elems = [
        _el("| A | B |\n|---|---|\n| 1 | 2 |", "table", page_num=1),
        _el("----|----|\n| 3 | 4 |", "table", page_num=2),
    ]
    chunks = c.chunk(elems, book_id="b", source_file="f.pdf")
    assert len(chunks) == 2


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


def test_same_stem_different_ext_no_chunk_id_collision():
    """book.pdf 与 book.epub 双格式 ingest 时 chunk_id 不得相同。"""
    c = Chunker()
    pdf_chunks = c.chunk([_el("Same content.", page_num=3)], book_id="b", source_file="book.pdf")
    epub_chunks = c.chunk([_el("Same content.", page_num=3)], book_id="b", source_file="book.epub")
    assert pdf_chunks[0].chunk_id != epub_chunks[0].chunk_id
    assert "book.pdf" in pdf_chunks[0].chunk_id
    assert "book.epub" in epub_chunks[0].chunk_id
