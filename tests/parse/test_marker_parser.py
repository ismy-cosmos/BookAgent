"""Tests for MarkerParser — marker API is mocked; no model weights loaded."""
import io
from unittest.mock import MagicMock, patch

import pytest
import pypdfium2 as pdfium
from PIL import Image as PILImage

from pipeline.parse import Element
from pipeline.parse.marker import (
    MarkerParser,
    _PAGE_SEP,
    _classify_block,
    _markdown_to_elements,
    _rendered_to_elements,
)


# ── _classify_block ────────────────────────────────────────────────────────────

def test_classify_code_block():
    block = "```python\nprint('hello')\n```"
    etype, content = _classify_block(block)
    assert etype == "code"
    assert "print" in content
    assert "```" not in content


def test_classify_code_block_no_lang():
    block = "```\nx = 1\n```"
    etype, content = _classify_block(block)
    assert etype == "code"
    assert content == "x = 1"


def test_classify_formula_block():
    block = "$$\nE = mc^2\n$$"
    etype, content = _classify_block(block)
    assert etype == "formula"
    assert "mc^2" in content


def test_classify_formula_inline_wrap():
    block = "$$F = ma$$"
    etype, content = _classify_block(block)
    assert etype == "formula"
    assert content == "F = ma"


def test_classify_table():
    block = "| A | B |\n|---|---|\n| 1 | 2 |"
    etype, content = _classify_block(block)
    assert etype == "table"
    assert content == block


def test_classify_figure():
    block = "![Figure 1](fig1.png)"
    etype, content = _classify_block(block)
    assert etype == "figure"


def test_classify_text_paragraph():
    block = "This is a paragraph about attention mechanisms."
    etype, content = _classify_block(block)
    assert etype == "text"
    assert content == block


def test_classify_heading_as_text():
    block = "## Section 2: Introduction"
    etype, content = _classify_block(block)
    assert etype == "text"


# ── _markdown_to_elements ──────────────────────────────────────────────────────

def test_markdown_splits_blocks_and_assigns_page_num():
    md = "# Heading\n\nA paragraph.\n\n| A | B |\n|---|---|\n| 1 | 2 |"
    elements = _markdown_to_elements(md, page_num=3)
    assert len(elements) == 3
    assert all(e.page_num == 3 for e in elements)
    assert [e.type for e in elements] == ["text", "text", "table"]


def test_markdown_skips_empty_blocks():
    md = "Para 1\n\n\n\n\nPara 2"
    elements = _markdown_to_elements(md, page_num=1)
    assert len(elements) == 2


def test_markdown_empty_string_returns_empty():
    assert _markdown_to_elements("", page_num=1) == []


# ── _rendered_to_elements (paginate_output split) ─────────────────────────────

def _make_rendered(markdown: str):
    r = MagicMock()
    r.markdown = markdown
    return r


def _paginated(*page_contents: str) -> str:
    """Build a paginated markdown string matching marker's paginate_output format."""
    # marker prepends artifact section before the first page separator
    return "{0}\n\n" + f"\n\n{_PAGE_SEP}\n\n".join([""] + list(page_contents))


def test_rendered_two_pages_get_correct_page_nums():
    md = _paginated("Page one content.", "Page two content.")
    elements = _rendered_to_elements(_make_rendered(md), page_sep=_PAGE_SEP)
    assert len(elements) == 2
    assert elements[0].page_num == 1
    assert elements[1].page_num == 2


def test_rendered_three_pages():
    md = _paginated("Alpha.", "Beta.", "Gamma.")
    elements = _rendered_to_elements(_make_rendered(md), page_sep=_PAGE_SEP)
    pages = [e.page_num for e in elements]
    assert pages == [1, 2, 3]


def test_rendered_artifact_section_produces_no_elements():
    """sections[0] (pre-page artifact) must never appear in output."""
    md = "{0}\n\n" + _PAGE_SEP + "\n\nReal content."
    elements = _rendered_to_elements(_make_rendered(md), page_sep=_PAGE_SEP)
    assert len(elements) == 1
    assert elements[0].page_num == 1
    assert "Real" in elements[0].content


def test_rendered_empty_markdown_returns_empty():
    assert _rendered_to_elements(_make_rendered(""), page_sep=_PAGE_SEP) == []


def test_rendered_page_with_mixed_types():
    md = _paginated("# Heading\n\nText.\n\n$$E=mc^2$$")
    elements = _rendered_to_elements(_make_rendered(md), page_sep=_PAGE_SEP)
    assert [e.type for e in elements] == ["text", "text", "formula"]
    assert all(e.page_num == 1 for e in elements)


def test_rendered_uses_whatever_separator_it_is_given():
    """The split must use the passed-in separator, not a hardcoded one —
    this is what lets MarkerParser stay correct if marker-pdf's default
    page_separator ever changes."""
    custom_sep = "===PAGEBREAK==="
    md = "{0}\n\n" + f"\n\n{custom_sep}\n\n".join(["", "Page one.", "Page two."])
    elements = _rendered_to_elements(_make_rendered(md), page_sep=custom_sep)
    assert len(elements) == 2
    assert elements[0].page_num == 1
    assert elements[1].page_num == 2


# ── _split_markdown_blocks / _markdown_to_elements: blocks with internal blank lines ──

def test_markdown_code_block_with_internal_blank_line_stays_one_block():
    """A fenced code block with a blank line between functions must not be
    split into a broken 'half text + half code' pair."""
    md = "```c\nint foo() {\n    return 1;\n}\n\nint bar() {\n    return 2;\n}\n```"
    elements = _markdown_to_elements(md, page_num=1)
    assert len(elements) == 1
    assert elements[0].type == "code"
    assert "foo" in elements[0].content
    assert "bar" in elements[0].content
    assert "```" not in elements[0].content


def test_markdown_math_block_with_internal_blank_line_stays_one_block():
    md = "$$\nx = 1\n\ny = 2\n$$"
    elements = _markdown_to_elements(md, page_num=1)
    assert len(elements) == 1
    assert elements[0].type == "formula"
    assert "x = 1" in elements[0].content
    assert "y = 2" in elements[0].content


def test_markdown_code_block_surrounded_by_paragraphs():
    md = "Intro text.\n\n```python\ndef f():\n\n    return 1\n```\n\nOutro text."
    elements = _markdown_to_elements(md, page_num=1)
    assert [e.type for e in elements] == ["text", "code", "text"]
    assert "f()" in elements[1].content or "def f" in elements[1].content


# ── {N} pagination marker stripping ───────────────────────────────────────────

def _paginated_real(*page_contents: str, page_sep: str = _PAGE_SEP) -> str:
    """Build markdown exactly as marker produces with paginate_output=True.

    Format: \n\n{page_id}[sep]\n\n[content] repeated for each page.
    sections[1] will end with \n\n{1} (next page's marker artifact).
    """
    parts = [f"\n\n{{{i}}}{page_sep}\n\n{content}" for i, content in enumerate(page_contents)]
    return "".join(parts)


def test_pagination_markers_not_emitted_as_elements():
    """{N} artifacts left at end of each section after split must not appear
    as elements — they are marker's internal page IDs, not content."""
    md = _paginated_real("Page one content.", "Page two content.", "Page three content.")
    r = _make_rendered(md)
    elements = _rendered_to_elements(r, page_sep=_PAGE_SEP)
    for elem in elements:
        assert not __import__("re").fullmatch(r"\{\d+\}", elem.content.strip()), (
            f"Pagination artifact found as element: {elem.content!r}"
        )


def test_pagination_markers_stripped_page_count_correct():
    """{N} stripping must not drop real content or create phantom elements."""
    md = _paginated_real("Alpha.", "Beta.", "Gamma.")
    r = _make_rendered(md)
    elements = _rendered_to_elements(r, page_sep=_PAGE_SEP)
    assert len(elements) == 3
    contents = [e.content for e in elements]
    assert "Alpha." in contents
    assert "Beta." in contents
    assert "Gamma." in contents


def test_real_brace_digit_in_content_not_stripped():
    """A paragraph whose last line is text containing {3} (not a bare marker)
    must survive — only a standalone paragraph of exactly {N} is an artifact."""
    md = _paginated_real("The value is {3} and more text.", "Next page.")
    r = _make_rendered(md)
    elements = _rendered_to_elements(r, page_sep=_PAGE_SEP)
    page1_elem = next(e for e in elements if e.page_num == 1)
    assert "{3}" in page1_elem.content


# ── MarkerParser.parse (mocked converter) ─────────────────────────────────────

def _fake_rendered(markdown: str):
    r = MagicMock()
    r.markdown = markdown
    return r


def test_parse_per_page_correct_page_nums(tmp_path):
    pdf = tmp_path / "test.pdf"
    _make_blank_pdf(str(pdf), 2)

    md = _paginated("# Chapter One\n\nFirst.", "# Chapter Two\n\nSecond.")
    elems = _rendered_to_elements(_fake_rendered(md), page_sep=_PAGE_SEP)

    with patch("pipeline.parse.marker_worker_client.MarkerWorkerClient.submit",
               return_value=(elems, 2)) as mock_submit:
        elements = MarkerParser().parse(str(pdf))

    assert len(elements) == 4
    assert elements[0].page_num == 1
    assert elements[1].page_num == 1
    assert elements[2].page_num == 2
    assert elements[3].page_num == 2
    mock_submit.assert_called_once()


def test_parse_empty_pdf_returns_empty(tmp_path):
    pdf = tmp_path / "test.pdf"
    _make_blank_pdf(str(pdf), 2)

    with patch("pipeline.parse.marker_worker_client.MarkerWorkerClient.submit",
               return_value=([], 0)):
        elements = MarkerParser().parse(str(pdf))

    assert elements == []


def test_parse_returns_element_instances(tmp_path):
    pdf = tmp_path / "test.pdf"
    _make_blank_pdf(str(pdf), 2)

    md = _paginated("Some text.\n\n$$x^2$$")
    elems = _rendered_to_elements(_fake_rendered(md), page_sep=_PAGE_SEP)

    with patch("pipeline.parse.marker_worker_client.MarkerWorkerClient.submit",
               return_value=(elems, 1)):
        elements = MarkerParser().parse(str(pdf))

    assert all(isinstance(e, Element) for e in elements)
    types = {e.type for e in elements}
    assert "text" in types
    assert "formula" in types


# ── figure 元素附带图片字节 + release_models ─────────────────────────────────

def _rendered_with_images(markdown: str, images: dict):
    r = MagicMock()
    r.markdown = markdown
    r.images = images
    return r


def test_figure_element_gets_image_bytes_from_rendered_images():
    md = _paginated("![fig](_page_1_Picture_1.jpeg)")
    pil = PILImage.new("RGB", (10, 10), color="blue")
    r = _rendered_with_images(md, {"_page_1_Picture_1.jpeg": pil})

    elements = _rendered_to_elements(r, page_sep=_PAGE_SEP)

    fig = next(e for e in elements if e.type == "figure")
    img = PILImage.open(io.BytesIO(fig.metadata["image_bytes"]))
    assert img.size == (10, 10)


def test_figure_element_without_matching_image_has_no_bytes():
    md = _paginated("![fig](missing.jpeg)")
    r = _rendered_with_images(md, {})

    elements = _rendered_to_elements(r, page_sep=_PAGE_SEP)

    fig = next(e for e in elements if e.type == "figure")
    assert "image_bytes" not in fig.metadata


def test_release_models_clears_cached_converter():
    MarkerParser._converter = MagicMock()
    MarkerParser._page_sep = "x"
    with patch("pipeline.parse.marker_worker_client.MarkerWorkerClient.shutdown"):
        MarkerParser.release_models()
    assert MarkerParser._converter is None
    assert MarkerParser._page_sep is None


def test_release_models_noop_when_not_loaded():
    MarkerParser._converter = None
    with patch("pipeline.parse.marker_worker_client.MarkerWorkerClient.shutdown"):
        MarkerParser.release_models()
    assert MarkerParser._converter is None


# ── Worker routing ───────────────────────────────────────────────────

def test_parse_default_routes_to_worker(tmp_path):
    pdf_path = str(tmp_path / "test.pdf")
    _make_blank_pdf(pdf_path, 2)

    elems = _rendered_to_elements(_fake_rendered(
        _paginated("Content.")), page_sep=_PAGE_SEP)

    with patch("pipeline.parse.marker_worker_client.MarkerWorkerClient.submit",
               return_value=(elems, 1)) as mock_submit:
        MarkerParser().parse(str(pdf_path))
    assert mock_submit.called


def test_parse_disabled_env_routes_to_in_process(tmp_path):
    pdf_path = str(tmp_path / "test.pdf")
    _make_blank_pdf(pdf_path, 2)

    md = _paginated("Content.")
    mock_converter = MagicMock(return_value=_fake_rendered(md))

    with patch.dict("os.environ", {"MARKER_WORKER_DISABLED": "1"}):
        with patch.object(MarkerParser, "_get_converter", return_value=mock_converter), \
             patch.object(MarkerParser, "_page_sep", _PAGE_SEP):
            elements = MarkerParser().parse(str(pdf_path))
    assert len(elements) == 1
    assert mock_converter.called


def test_release_models_shuts_down_worker():
    MarkerParser._converter = MagicMock()
    MarkerParser._page_sep = "x"
    with patch("pipeline.parse.marker_worker_client.MarkerWorkerClient.shutdown") as mock_sd:
        MarkerParser.release_models()
    mock_sd.assert_called_once()
    assert MarkerParser._converter is None
    assert MarkerParser._page_sep is None


# ── 分隔符防碰撞 ────────────────────────────────────────────────────────────

def test_get_converter_configures_custom_page_separator():
    MarkerParser._converter = None
    MarkerParser._page_sep = None
    try:
        with patch("marker.converters.pdf.PdfConverter") as MockConverterCls, \
             patch("marker.models.create_model_dict", return_value={}):
            mock_instance = MockConverterCls.return_value
            mock_instance.resolve_dependencies.return_value.page_separator = _PAGE_SEP
            MarkerParser._get_converter()

        _, kwargs = MockConverterCls.call_args
        assert kwargs["config"]["page_separator"] == _PAGE_SEP
        assert kwargs["config"]["paginate_output"] is True
    finally:
        MarkerParser._converter = None
        MarkerParser._page_sep = None


# ── _pdf_page_count / _write_page_range_pdf (real pypdfium2, no marker/ML) ────

def _make_blank_pdf(path: str, num_pages: int) -> None:
    """构造一个真实、可被 pypdfium2 打开的最小多页 PDF，不依赖任何外部语料文件。"""
    doc = pdfium.PdfDocument.new()
    for _ in range(num_pages):
        doc.new_page(200, 200)
    with open(path, "wb") as f:
        doc.save(f)
    doc.close()


def test_pdf_page_count_counts_real_pages(tmp_path):
    from pipeline.parse.marker import _pdf_page_count
    pdf_path = str(tmp_path / "blank.pdf")
    _make_blank_pdf(pdf_path, 7)
    assert _pdf_page_count(pdf_path) == 7


def test_write_page_range_pdf_extracts_correct_page_count(tmp_path):
    from pipeline.parse.marker import _pdf_page_count, _write_page_range_pdf
    src_path = str(tmp_path / "blank.pdf")
    _make_blank_pdf(src_path, 10)
    dest_path = str(tmp_path / "batch.pdf")
    _write_page_range_pdf(src_path, 3, 8, dest_path)
    assert _pdf_page_count(dest_path) == 5


def test_write_page_range_pdf_first_batch(tmp_path):
    from pipeline.parse.marker import _pdf_page_count, _write_page_range_pdf
    src_path = str(tmp_path / "blank.pdf")
    _make_blank_pdf(src_path, 6)
    dest_path = str(tmp_path / "batch0.pdf")
    _write_page_range_pdf(src_path, 0, 3, dest_path)
    assert _pdf_page_count(dest_path) == 3


# ── _parse_in_batches ──────────────────────────────────────────────────────

def test_parse_in_batches_assigns_absolute_page_numbers(tmp_path):
    import pipeline.parse.marker as marker_module

    pdf_path = str(tmp_path / "big.pdf")
    _make_blank_pdf(pdf_path, 6)

    batch1_elems = _rendered_to_elements(_fake_rendered(
        _paginated("Page one.", "Page two.", "Page three.")), page_sep=_PAGE_SEP)
    batch2_elems = _rendered_to_elements(_fake_rendered(
        _paginated("Page four.", "Page five.", "Page six.")), page_sep=_PAGE_SEP)
    mock_render = MagicMock(side_effect=[(batch1_elems, 3), (batch2_elems, 3)])

    with patch.object(marker_module, "_BATCH_SIZE_PAGES", 3):
        elements = marker_module._parse_in_batches(
            mock_render, pdf_path, total_pages=6,
            should_pause=lambda: False,
        )

    assert [e.page_num for e in elements] == [1, 2, 3, 4, 5, 6]
    assert mock_render.call_count == 2


def test_parse_in_batches_single_batch_when_under_threshold(tmp_path):
    import pipeline.parse.marker as marker_module

    pdf_path = str(tmp_path / "small.pdf")
    _make_blank_pdf(pdf_path, 3)

    md = _paginated("Alpha.", "Beta.", "Gamma.")
    elements = _rendered_to_elements(_fake_rendered(md), page_sep=_PAGE_SEP)
    mock_render = MagicMock(return_value=(elements, 3))

    result = marker_module._parse_in_batches(
        mock_render, pdf_path, total_pages=3,
        should_pause=lambda: False,
    )

    assert [e.page_num for e in result] == [1, 2, 3]
    assert mock_render.call_count == 1


def test_parse_in_batches_warns_on_page_count_mismatch(tmp_path, capsys):
    import pipeline.parse.marker as marker_module

    pdf_path = str(tmp_path / "big.pdf")
    _make_blank_pdf(pdf_path, 3)

    # Only 2 pages rendered but batch expected 3
    mismatched_md = _paginated("Page one.", "Page two.")
    mismatched_elements = _rendered_to_elements(_fake_rendered(mismatched_md), page_sep=_PAGE_SEP)
    mock_render = MagicMock(return_value=(mismatched_elements, 2))  # 2 sections, expected 3 → mismatch

    result = marker_module._parse_in_batches(
        mock_render, pdf_path, total_pages=3,
        should_pause=lambda: False,
    )

    captured = capsys.readouterr()
    assert "[warn]" in captured.out
    assert "期望 3 页" in captured.out
    assert "实际渲染 2 段" in captured.out
    assert len(result) == 2


def test_parse_dispatches_to_batches_when_over_threshold(tmp_path):
    import pipeline.parse.marker as marker_module

    pdf_path = str(tmp_path / "big.pdf")
    _make_blank_pdf(pdf_path, 4)

    # Each batch returns fresh elements — production code mutates page_num in place
    def _render_side_effect(pdf_path, expected_pages, should_pause=None):
        elems = _rendered_to_elements(_fake_rendered(
            _paginated("One.", "Two.")), page_sep=_PAGE_SEP)
        return elems, 2

    with patch.object(marker_module, "_BATCH_SIZE_PAGES", 2), \
         patch("pipeline.parse.marker_worker_client.MarkerWorkerClient.submit",
               side_effect=_render_side_effect) as mock_submit:
        elements = MarkerParser().parse(str(pdf_path))

    assert mock_submit.call_count == 2
    assert [e.page_num for e in elements] == [1, 2, 3, 4]


def test_parse_stays_single_call_when_under_threshold(tmp_path):
    pdf_path = str(tmp_path / "small.pdf")
    _make_blank_pdf(pdf_path, 2)

    md = _paginated("Only page.", "Second page.")
    batch_elements = _rendered_to_elements(_fake_rendered(md), page_sep=_PAGE_SEP)

    with patch("pipeline.parse.marker_worker_client.MarkerWorkerClient.submit",
               return_value=(batch_elements, 2)) as mock_submit:
        elements = MarkerParser().parse(str(pdf_path))

    mock_submit.assert_called_once()
    assert [e.page_num for e in elements] == [1, 2]


# ── 批次级暂停 ─────────────────────────────────────────────────────────────

def test_parse_in_batches_pause_raises_before_next_batch(tmp_path):
    import pipeline.parse.marker as marker_module

    pdf_path = str(tmp_path / "big.pdf")
    _make_blank_pdf(pdf_path, 6)

    md = _paginated("One.", "Two.", "Three.")
    batch_elements = _rendered_to_elements(_fake_rendered(md), page_sep=_PAGE_SEP)
    mock_render = MagicMock(return_value=(batch_elements, 3))

    calls = {"n": 0}
    def pause_after_first_batch():
        calls["n"] += 1
        return calls["n"] > 1

    with patch.object(marker_module, "_BATCH_SIZE_PAGES", 3):
        with pytest.raises(marker_module.MarkerParsePaused):
            marker_module._parse_in_batches(
                mock_render, pdf_path, total_pages=6,
                should_pause=pause_after_first_batch,
            )

    assert mock_render.call_count == 1


def test_parse_in_batches_no_pause_completes_normally(tmp_path):
    import pipeline.parse.marker as marker_module

    pdf_path = str(tmp_path / "big.pdf")
    _make_blank_pdf(pdf_path, 4)

    md = _paginated("One.", "Two.")
    batch_elements = _rendered_to_elements(_fake_rendered(md), page_sep=_PAGE_SEP)
    mock_render = MagicMock(return_value=(batch_elements, 2))

    with patch.object(marker_module, "_BATCH_SIZE_PAGES", 2):
        elements = marker_module._parse_in_batches(
            mock_render, pdf_path, total_pages=4,
            should_pause=lambda: False,
        )

    assert mock_render.call_count == 2
    assert len(elements) == 4