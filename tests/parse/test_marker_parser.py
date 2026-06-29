"""Tests for MarkerParser — marker API is mocked; no model weights loaded."""
from unittest.mock import MagicMock, patch

import pytest

from pipeline.parse import Element
from pipeline.parse.marker import (
    MarkerParser,
    _classify_block,
    _markdown_to_elements,
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


# ── MarkerParser.parse (mocked converter) ─────────────────────────────────────

def _fake_rendered(markdown: str, children=None):
    r = MagicMock()
    r.markdown = markdown
    r.children = children
    return r


def test_parse_fallback_when_no_children(tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    rendered = _fake_rendered("# Title\n\nParagraph.", children=None)
    mock_converter = MagicMock(return_value=rendered)

    with patch.object(MarkerParser, "_get_converter", return_value=mock_converter):
        elements = MarkerParser().parse(str(pdf))

    assert len(elements) == 2
    assert all(e.page_num == 0 for e in elements)
    assert isinstance(elements[0], Element)


def test_parse_uses_children_page_ids(tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    page0 = MagicMock()
    page0.page_id = 0
    page0.markdown = "Page one content."
    page1 = MagicMock()
    page1.page_id = 1
    page1.markdown = "Page two content."

    rendered = _fake_rendered("ignored", children=[page0, page1])
    mock_converter = MagicMock(return_value=rendered)

    with patch.object(MarkerParser, "_get_converter", return_value=mock_converter):
        elements = MarkerParser().parse(str(pdf))

    assert len(elements) == 2
    assert elements[0].page_num == 1  # page_id 0 → page_num 1
    assert elements[1].page_num == 2


def test_parse_returns_element_instances(tmp_path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    rendered = _fake_rendered("Some text.\n\n$$x^2$$", children=None)
    mock_converter = MagicMock(return_value=rendered)

    with patch.object(MarkerParser, "_get_converter", return_value=mock_converter):
        elements = MarkerParser().parse(str(pdf))

    assert all(isinstance(e, Element) for e in elements)
    types = {e.type for e in elements}
    assert "text" in types
    assert "formula" in types
