from __future__ import annotations
import re


def _mml_to_latex(node) -> str:
    """Recursively convert a BeautifulSoup MathML node to LaTeX string."""
    from bs4 import NavigableString
    if isinstance(node, NavigableString):
        return str(node)
    tag = node.name
    children = [_mml_to_latex(c) for c in node.children]
    children = [c for c in children if c.strip()]

    if tag == "mfrac" and len(children) >= 2:
        return rf"\frac{{{children[0]}}}{{{children[1]}}}"
    if tag == "msup" and len(children) >= 2:
        return rf"{children[0]}^{{{children[1]}}}"
    if tag == "msub" and len(children) >= 2:
        return rf"{children[0]}_{{{children[1]}}}"
    if tag == "msqrt" and children:
        return rf"\sqrt{{{children[0]}}}"
    if tag == "mroot" and len(children) >= 2:
        return rf"\sqrt[{children[1]}]{{{children[0]}}}"
    if tag == "mrow":
        return "".join(children)
    if tag in ("mi", "mn", "mo", "mtext", "ms"):
        return node.get_text()
    if tag == "math":
        return "".join(children)
    return node.get_text()


def _table_to_markdown(table_tag) -> str:
    """Convert a <table> BS4 tag to Markdown table string."""
    rows = table_tag.find_all("tr")
    md_rows: list[str] = []
    for i, row in enumerate(rows):
        cells = [td.get_text(strip=True) for td in row.find_all(["th", "td"])]
        md_rows.append("| " + " | ".join(cells) + " |")
        if i == 0:
            md_rows.append("| " + " | ".join(["---"] * len(cells)) + " |")
    return "\n".join(md_rows)


def _html_to_elements(html: str) -> list:
    """Parse an HTML string into a list of Element objects (page_num always 0)."""
    from bs4 import BeautifulSoup, NavigableString, Tag
    from pipeline.parse.base import Element

    soup = BeautifulSoup(html, "lxml")
    body = soup.find("body") or soup
    elements: list[Element] = []

    _HEADING_LEVEL = {"h1": "#", "h2": "##", "h3": "###", "h4": "####"}

    for tag in body.find_all(["h1", "h2", "h3", "h4", "p", "pre", "table"], recursive=True):
        tag_name = tag.name

        if tag_name in _HEADING_LEVEL:
            text = tag.get_text(strip=True)
            if not text:
                continue
            content = f"{_HEADING_LEVEL[tag_name]} {text}"
            elements.append(Element(type="text", content=content, page_num=0))

        elif tag_name == "p":
            # Replace <math> nodes with $$...$$ LaTeX
            for math_tag in tag.find_all("math"):
                latex = _mml_to_latex(math_tag)
                math_tag.replace_with(f"$${latex}$$")
            text = tag.get_text(separator=" ", strip=True)
            text = re.sub(r"\s+", " ", text).strip()
            if not text:
                continue
            elements.append(Element(type="text", content=text, page_num=0))

        elif tag_name == "pre":
            code = tag.get_text()
            if code.strip():
                elements.append(Element(type="code", content=code.strip(), page_num=0))

        elif tag_name == "table":
            md = _table_to_markdown(tag)
            if md.strip():
                elements.append(Element(type="table", content=md, page_num=0))

    return elements


class EPUBParser:
    """Parse EPUB files into Element lists using ebooklib + BeautifulSoup."""

    def parse(self, epub_path: str) -> list:
        import ebooklib.epub as epub_lib
        from pipeline.parse.base import Element

        book = epub_lib.read_epub(epub_path)
        all_elements: list = []

        for i, (item_id, _linear) in enumerate(book.spine):
            item = book.get_item_with_id(item_id)
            if item is None:
                continue
            html = item.get_content().decode("utf-8", errors="replace")
            spine_elements = _html_to_elements(html)
            if i > 0 and spine_elements:
                all_elements.append(Element(type="section_break", content="", page_num=0))
            all_elements.extend(spine_elements)

        return all_elements
