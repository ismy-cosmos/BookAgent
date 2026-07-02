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
    assert "x" in result and "2" in result and ("^" in result or "sup" in result.lower())


def test_mml_to_latex_plain_text():
    from bs4 import BeautifulSoup
    mml = "<math><mi>E</mi><mo>=</mo><mi>m</mi><mi>c</mi></math>"
    soup = BeautifulSoup(mml, "xml")
    result = _mml_to_latex(soup.find("math"))
    assert "E" in result


def test_mml_to_latex_subscript_superscript():
    from bs4 import BeautifulSoup
    mml = "<math><msubsup><mi>x</mi><mi>i</mi><mn>2</mn></msubsup></math>"
    soup = BeautifulSoup(mml, "xml")
    result = _mml_to_latex(soup.find("math"))
    assert "x" in result and "i" in result and "2" in result
    assert "_" in result and "^" in result


def test_mml_to_latex_munder():
    from bs4 import BeautifulSoup
    mml = "<math><munder><mo>lim</mo><mrow><mi>n</mi><mo>→</mo><mo>∞</mo></mrow></munder></math>"
    soup = BeautifulSoup(mml, "xml")
    result = _mml_to_latex(soup.find("math"))
    assert "lim" in result
    assert "underset" in result or "n" in result


def test_mml_to_latex_mover():
    from bs4 import BeautifulSoup
    mml = "<math><mover><mi>x</mi><mo>→</mo></mover></math>"
    soup = BeautifulSoup(mml, "xml")
    result = _mml_to_latex(soup.find("math"))
    assert "x" in result
    assert "overset" in result or "over" in result.lower()


def test_mml_to_latex_mfenced():
    from bs4 import BeautifulSoup
    mml = '<math><mfenced open="[" close="]"><mi>x</mi></mfenced></math>'
    soup = BeautifulSoup(mml, "xml")
    result = _mml_to_latex(soup.find("math"))
    assert "x" in result
    assert "[" in result or "left" in result.lower()


def test_mml_to_latex_mtable():
    from bs4 import BeautifulSoup
    mml = """<math><mtable>
      <mtr><mtd><mn>1</mn></mtd><mtd><mn>0</mn></mtd></mtr>
      <mtr><mtd><mn>0</mn></mtd><mtd><mn>1</mn></mtd></mtr>
    </mtable></math>"""
    soup = BeautifulSoup(mml, "xml")
    result = _mml_to_latex(soup.find("math"))
    assert "pmatrix" in result
    assert "1" in result and "0" in result
    assert "&" in result


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


def test_html_to_elements_list_items_not_dropped():
    """<ul>/<li> 内容目前会被静默丢弃——这个测试记录正确行为，目前应该失败。"""
    html = """<html><body>
    <p>Intro text.</p>
    <ul><li>First item</li><li>Second item</li></ul>
    <p>Outro text.</p>
    </body></html>"""
    elems = _html_to_elements(html)
    all_content = " ".join(e.content for e in elems)
    assert "First item" in all_content
    assert "Second item" in all_content


def test_html_to_elements_blockquote_not_dropped():
    """<blockquote> 内容目前会被静默丢弃——这个测试记录正确行为，目前应该失败。"""
    html = "<html><body><p>Before.</p><blockquote><p>A quoted passage.</p></blockquote><p>After.</p></body></html>"
    elems = _html_to_elements(html)
    all_content = " ".join(e.content for e in elems)
    assert "A quoted passage" in all_content


def test_html_to_elements_img_becomes_figure():
    """<img> 目前会被静默丢弃，应该生成一个 figure 类型的 Element——这个测试目前应该失败。"""
    html = '<html><body><p>Before.</p><img src="fig1.png" alt="A diagram"/><p>After.</p></body></html>'
    elems = _html_to_elements(html)
    assert any(e.type == "figure" for e in elems)


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


def test_html_to_elements_page_num_param():
    html = "<html><body><p>Hello.</p></body></html>"
    elems = _html_to_elements(html, page_num=3)
    assert elems[0].page_num == 3


def test_epub_parser_page_num_is_spine_position(tmp_path):
    epub_path = str(tmp_path / "book.epub")
    spine_item_1 = MagicMock()
    spine_item_1.get_content.return_value = b"<html><body><p>Chapter one.</p></body></html>"
    spine_item_1.get_name.return_value = "text/ch1.html"
    spine_item_2 = MagicMock()
    spine_item_2.get_content.return_value = b"<html><body><p>Chapter two.</p></body></html>"
    spine_item_2.get_name.return_value = "text/ch2.html"

    mock_book = MagicMock()
    mock_book.spine = [("id1", "yes"), ("id2", "yes")]
    mock_book.get_item_with_id.side_effect = lambda id_: {
        "id1": spine_item_1, "id2": spine_item_2
    }[id_]

    with patch("ebooklib.epub.read_epub", return_value=mock_book):
        elems = EPUBParser().parse(epub_path)

    ch1 = next(e for e in elems if "Chapter one" in e.content)
    ch2 = next(e for e in elems if "Chapter two" in e.content)
    assert ch1.page_num == 1
    assert ch2.page_num == 2
