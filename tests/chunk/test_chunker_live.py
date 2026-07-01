"""Live integration test: MarkerParser → Chunker → chunk metadata quality.

Runs the real ML model stack against a real PDF. Slow (loads marker weights).
Guards against regressions in the full parse→chunk chain that unit tests
with mocked/synthetic input cannot catch.

Verified properties:
  - No {N} pagination artifacts survive into chunk content (parser fix)
  - No micro-fragments: packing keeps chunks above a minimum useful size (packing fix)
  - page_start / page_end are valid 1-indexed, non-None, end >= start
  - token_count matches actual content length
  - chunk_ids are unique and follow the expected format
"""
import os
import re

import pytest

from pipeline.chunk import Chunker
from pipeline.chunk.chunker import _token_count
from pipeline.parse.marker import MarkerParser

_PDF_PATH = "eval/testset/cs/raw/book/cpu-intro.pdf"
_BOOK_ID = "ostep-cs"

_PAGE_MARKER_RE = re.compile(r"^\s*\{\d+\}\s*$")
_CHUNK_ID_RE = re.compile(r"^[^/]+/[^/]+/p(\d{4}|None)/\d{4}$")

# Minimum token count we'll accept for a chunk produced from a real PDF page.
# A real page has at least a heading + a sentence; anything below this is a
# micro-fragment symptom of the packing regression.
_MIN_USEFUL_TOKENS = 10


@pytest.fixture(scope="module")
def chunks():
    elements = MarkerParser().parse(_PDF_PATH)
    return Chunker().chunk(elements, book_id=_BOOK_ID, source_file="cpu-intro.pdf")


@pytest.mark.skipif(not os.path.exists(_PDF_PATH), reason="corpus PDF not present")
def test_no_pagination_artifact_chunks(chunks):
    """{N} pagination markers must not appear as chunk content."""
    bad = [c for c in chunks if _PAGE_MARKER_RE.fullmatch(c.content)]
    assert not bad, (
        f"{len(bad)} chunks contain bare {{N}} pagination artifacts: "
        + ", ".join(c.chunk_id for c in bad[:5])
    )


@pytest.mark.skipif(not os.path.exists(_PDF_PATH), reason="corpus PDF not present")
def test_no_micro_fragment_chunks(chunks):
    """No chunk should be a micro-fragment — packing must combine short sentences.

    Regression: without the buf/buf_tok accumulation, a 533-token homework list
    splintered into 32 pieces averaging ~16 tokens each.
    """
    bad = [c for c in chunks if c.token_count < _MIN_USEFUL_TOKENS]
    assert not bad, (
        f"{len(bad)} micro-fragment chunks (< {_MIN_USEFUL_TOKENS} tokens): "
        + ", ".join(f"{c.chunk_id}({c.token_count}t)" for c in bad[:10])
    )


@pytest.mark.skipif(not os.path.exists(_PDF_PATH), reason="corpus PDF not present")
def test_page_metadata_valid(chunks):
    """page_start and page_end must be 1-indexed, non-None, and end >= start."""
    for c in chunks:
        assert c.page_start is not None, f"{c.chunk_id}: page_start is None"
        assert c.page_end is not None, f"{c.chunk_id}: page_end is None"
        assert c.page_start >= 1, f"{c.chunk_id}: page_start={c.page_start} < 1"
        assert c.page_end >= c.page_start, (
            f"{c.chunk_id}: page_end={c.page_end} < page_start={c.page_start}"
        )


@pytest.mark.skipif(not os.path.exists(_PDF_PATH), reason="corpus PDF not present")
def test_token_count_matches_content(chunks):
    """token_count field must equal the actual token count of content."""
    for c in chunks:
        actual = _token_count(c.content)
        assert c.token_count == actual, (
            f"{c.chunk_id}: token_count={c.token_count} but content has {actual} tokens"
        )


@pytest.mark.skipif(not os.path.exists(_PDF_PATH), reason="corpus PDF not present")
def test_chunk_ids_unique(chunks):
    """chunk_ids must be globally unique within a source file."""
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids)), (
        f"Duplicate chunk_ids: {[i for i in ids if ids.count(i) > 1][:5]}"
    )


@pytest.mark.skipif(not os.path.exists(_PDF_PATH), reason="corpus PDF not present")
def test_chunk_id_format(chunks):
    """chunk_ids must match book_id/stem/pNNNN/NNNN format."""
    bad = [c for c in chunks if not _CHUNK_ID_RE.match(c.chunk_id)]
    assert not bad, (
        f"Malformed chunk_ids: {[c.chunk_id for c in bad[:5]]}"
    )


@pytest.mark.skipif(not os.path.exists(_PDF_PATH), reason="corpus PDF not present")
def test_summary(chunks, capsys):
    """Print a summary for human review — not a pass/fail assertion."""
    token_counts = [c.token_count for c in chunks]
    page_spans = [c.page_end - c.page_start for c in chunks if c.page_end and c.page_start]
    types = {}
    for c in chunks:
        types[c.element_type] = types.get(c.element_type, 0) + 1

    with capsys.disabled():
        print(f"\n── cpu-intro.pdf parse→chunk summary ──")
        print(f"  chunks: {len(chunks)}")
        print(f"  tokens: min={min(token_counts)} avg={sum(token_counts)//len(token_counts)} max={max(token_counts)}")
        print(f"  page span: max={max(page_spans) if page_spans else 'N/A'}")
        print(f"  element types: {types}")
