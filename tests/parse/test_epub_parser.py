from unittest.mock import MagicMock, patch
import pytest
from pipeline.parse import EPUBParser
from pipeline.parse.base import Element
from pipeline.parse.epub import _mml_to_latex, _html_to_elements


def test_mml_to_latex_fraction():
    from bs4 import BeautifulSoup
    mml = "<math><mfrac><mn>1</mn><mn>2</mn></mfrac></math>"
    soup = BeautifulSoup(mml, "xml")
    result = _mml_to_latex(soup.find("math"))
    assert "\\frac" in result
    assert "1" in result and "2" in result


def test_mml_to_latex_superscript():
    from bs4 import BeautifulSoup
    mml = "<math><msup><mi>x</mi><mn>2</mn></msup></math>"
    soup = BeautifulSoup(mml, "xml")
    result = _mml_to_latex(soup.find("math"))
    assert "x" in result
    assert "^" in result or "2" in result


def test_mml_to_latex_plain_text():
    from bs4 import BeautifulSoup
    mml = "<math><mi>E</mi><mo>=</mo><mi>m</mi><mi>c</mi></math>"
    soup = BeautifulSoup(mml, "xml")
    result = _mml_to_latex(soup.find("math"))
    assert "E" in result


def test_html_to_elements_heading():
    html = "<html><body><h2>Chapter 1</h2><p>Some text.</p></body></html>"
    elems = _html_to_elements(html)
    types = [e.type for e in elems]
    contents = [e.content for e in elems]
    assert "text" in types
    assert any("Chapter 1" in c for c in contents)
    heading_elem = next(e for e in elems if "Chapter 1" in e.content)
    assert heading_elem.content.startswith("#")


def test_html_to_elements_paragraph():
    html = "<html><body><p>Hello world.</p></body></html>"
    elems = _html_to_elements(html)
    assert len(elems) == 1
    assert elems[0].type == "text"
    assert elems[0].content == "Hello world."
    assert elems[0].page_num == 0


def test_html_to_elements_table():
    html = """<html><body>
    <table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>
    </body></html>"""
    elems = _html_to_elements(html)
    assert any(e.type == "table" for e in elems)
    table_elem = next(e for e in elems if e.type == "table")
    assert "A" in table_elem.content


def test_html_to_elements_code_block():
    html = "<html><body><pre><code>x = 1</code></pre></body></html>"
    elems = _html_to_elements(html)
    assert any(e.type == "code" for e in elems)


def test_html_to_elements_skips_empty():
    html = "<html><body><p>   </p><p>Real content.</p></body></html>"
    elems = _html_to_elements(html)
    assert len(elems) == 1
    assert "Real content" in elems[0].content


def test_epub_parser_inserts_section_breaks(tmp_path):
    epub_path = str(tmp_path / "book.epub")
    # Mock ebooklib to return 2 spine items
    spine_item_1 = MagicMock()
    spine_item_1.get_content.return_value = b"<html><body><p>Chapter one.</p></body></html>"
    spine_item_2 = MagicMock()
    spine_item_2.get_content.return_value = b"<html><body><p>Chapter two.</p></body></html>"

    mock_book = MagicMock()
    mock_book.spine = [("id1", "yes"), ("id2", "yes")]
    mock_book.get_item_with_id.side_effect = lambda id_: {
        "id1": spine_item_1, "id2": spine_item_2
    }[id_]

    with patch("ebooklib.epub.read_epub", return_value=mock_book):
        parser = EPUBParser()
        elems = parser.parse(epub_path)

    types = [e.type for e in elems]
    assert "section_break" in types
    # section_break is between spine items, not at start or end
    sb_idx = types.index("section_break")
    assert 0 < sb_idx < len(types) - 1
