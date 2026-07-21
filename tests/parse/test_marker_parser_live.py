"""Live integration test for MarkerParser — runs the REAL marker-pdf
PdfConverter (loads actual ML model weights) against a real PDF.

Unlike test_marker_parser.py (fully mocked, fast), this test exists
specifically to catch drift between our assumptions about marker-pdf's
behavior (e.g. the page_separator it emits under paginate_output=True)
and what the installed marker-pdf version actually does. A fully-mocked
test suite can stay green forever while the real library silently changes
underneath it; this test is the guard against that.

Slow: loads marker's layout/OCR models. Requires the eval/testset/cs raw
PDFs to be present on disk.
"""
import os
from unittest.mock import patch

import pytest

from pipeline.parse.marker import MarkerParser

_PDF_PATH = "eval/testset/cs/raw/book/cpu-intro.pdf"
_THREADS_INTRO_PATH = "eval/testset/cs/raw/book/threads-intro.pdf"


@pytest.mark.skipif(not os.path.exists(_PDF_PATH), reason="corpus PDF not present")
def test_marker_parser_real_pdf_no_page_zero():
    elements = MarkerParser().parse(_PDF_PATH)

    assert elements, "real PDF must produce elements"
    zero_page = [e for e in elements if e.page_num == 0]
    assert not zero_page, (
        f"{len(zero_page)} elements got page_num=0 — the page_separator "
        "MarkerParser derived from the live renderer did not match what "
        "the markdown actually contains"
    )


@pytest.mark.skipif(not os.path.exists(_PDF_PATH), reason="corpus PDF not present")
def test_marker_parser_real_pdf_page_count_matches_converter():
    converter = MarkerParser._get_converter()
    elements = MarkerParser().parse(_PDF_PATH)

    rendered = converter(_PDF_PATH)
    real_page_count = len(rendered.markdown.split(MarkerParser._page_sep)) - 1

    max_page_num = max(e.page_num for e in elements)
    assert max_page_num == real_page_count, (
        f"derived page_sep produced {max_page_num} pages from parse(), but "
        f"splitting the live converter's own output gives {real_page_count} — "
        "our separator assumption has drifted from the real renderer"
    )


@pytest.mark.skipif(not os.path.exists(_PDF_PATH), reason="corpus PDF not present")
def test_marker_parser_page_sep_is_derived_not_hardcoded():
    """MarkerParser._page_sep must come from the live renderer instance,
    not a guess baked into our source code."""
    MarkerParser._get_converter()
    resolved = MarkerParser._converter.resolve_dependencies(MarkerParser._converter.renderer)
    assert MarkerParser._page_sep == resolved.page_separator


@pytest.mark.skipif(not os.path.exists(_THREADS_INTRO_PATH), reason="corpus PDF not present")
def test_marker_parser_batched_matches_single_shot_page_count():
    """强制小批大小触发分批路径，验证跟单次整本解析页码总数一致（16页）。"""
    import pipeline.parse.marker as marker_module

    with patch.object(marker_module, "_BATCH_SIZE_PAGES", 5):
        elements = MarkerParser().parse(_THREADS_INTRO_PATH)

    max_page = max(e.page_num for e in elements)
    assert max_page == 16, (
        f"分批解析（batch_size=5）应产出16页，实际最大 page_num={max_page}——"
        "分隔符碰撞或跨批页码拼接可能有问题"
    )


@pytest.mark.skipif(not os.path.exists(_THREADS_INTRO_PATH), reason="corpus PDF not present")
def test_marker_parser_batched_table_not_split_at_batch_boundary():
    """真实案例：物理第6页的宽表格，换新分隔符后不应再被误切成两个chunk。
    强制 batch_size=5 让第6页恰好落在某一批的边界附近，验证物理切分不会
    像旧分隔符碰撞那样破坏这张表格的完整性。"""
    import pipeline.parse.marker as marker_module

    with patch.object(marker_module, "_BATCH_SIZE_PAGES", 5):
        elements = MarkerParser().parse(_THREADS_INTRO_PATH)

    page6_elements = [e for e in elements if e.page_num == 6]
    table_elements = [e for e in page6_elements if "Thread 1" in e.content and "Thread2" in e.content]
    assert len(table_elements) == 1, (
        f"第6页应该只有一个完整的 Thread1/Thread2 表格 element，实际找到 "
        f"{len(table_elements)} 个——可能被误切成了两段"
    )
    assert "|---" in table_elements[0].content or "|--" in table_elements[0].content, (
        "表格必须包含完整的分隔行，不能是缺分隔行的头部半截"
    )
