from __future__ import annotations
import re
from urllib.parse import unquote, urljoin


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
    if tag == "msubsup" and len(children) >= 3:
        return rf"{children[0]}_{{{children[1]}}}^{{{children[2]}}}"
    if tag == "munder" and len(children) >= 2:
        return rf"\underset{{{children[1]}}}{{{children[0]}}}"
    if tag == "mover" and len(children) >= 2:
        return rf"\overset{{{children[1]}}}{{{children[0]}}}"
    if tag == "mfenced":
        open_ch = node.get("open", "(")
        close_ch = node.get("close", ")")
        return rf"\left{open_ch}{''.join(children)}\right{close_ch}"
    if tag == "mtd":
        return "".join(children)
    if tag == "mtr":
        return " & ".join(c for c in children if c.strip())
    if tag == "mtable":
        rows = [c for c in children if c.strip()]
        return r"\begin{pmatrix}" + r" \\ ".join(rows) + r"\end{pmatrix}"
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


_HEADING_LEVEL = {"h1": "#", "h2": "##", "h3": "###", "h4": "####"}
_CONTAINER_TAGS = {"div", "section", "article", "main", "svg"}


def _resolve_href(base_href: str, src: str) -> str:
    """Resolve an image src relative to its chapter's package path.

    e.g. base_href='text/ch1.html', src='../images/x.jpg' -> 'images/x.jpg'
    Pure string math; no package I/O, no manifest validation.
    """
    return unquote(urljoin(base_href, src)).lstrip("/")


def _html_to_elements(html: str, page_num: int = 0, base_href: str = "") -> list:
    """Parse an HTML string into a list of Element objects.

    page_num: spine position (1-indexed) of the chapter this HTML came from;
              0 means unknown (chunker treats 0 as None).
    base_href: the chapter's own path inside the EPUB package, used to
               resolve relative image hrefs.
    """
    from bs4 import BeautifulSoup, Tag
    from pipeline.parse.base import Element

    soup = BeautifulSoup(html, "lxml")
    body = soup.find("body") or soup
    elements: list[Element] = []

    def emit_figure(img_tag: Tag) -> None:
        src = img_tag.get("src") or img_tag.get("xlink:href") or img_tag.get("href") or ""
        alt = (img_tag.get("alt") or "").strip()
        path = _resolve_href(base_href, src) if src else ""
        elements.append(Element(type="figure", content=f"![{alt}]({path})", page_num=page_num))

    def process_node(tag: Tag) -> None:
        tag_name = tag.name
        if tag_name in _HEADING_LEVEL:
            text = tag.get_text(strip=True)
            if text:
                elements.append(Element(
                    type="text",
                    content=f"{_HEADING_LEVEL[tag_name]} {text}",
                    page_num=page_num,
                ))
        elif tag_name == "p":
            for img_tag in tag.find_all("img"):
                emit_figure(img_tag)
                img_tag.decompose()
            for math_tag in tag.find_all("math"):
                latex = _mml_to_latex(math_tag)
                math_tag.replace_with(f"$${latex}$$")
            text = re.sub(r"\s+", " ", tag.get_text(separator=" ", strip=True)).strip()
            if text:
                elements.append(Element(type="text", content=text, page_num=page_num))
        elif tag_name == "pre":
            code = tag.get_text()
            if code.strip():
                elements.append(Element(type="code", content=code.strip(), page_num=page_num))
        elif tag_name == "table":
            md = _table_to_markdown(tag)
            if md.strip():
                elements.append(Element(type="table", content=md, page_num=page_num))
        elif tag_name == "math":
            latex = _mml_to_latex(tag)
            if latex.strip():
                elements.append(Element(type="formula", content=f"$${latex}$$", page_num=page_num))
        elif tag_name in ("ul", "ol"):
            lines: list[str] = []
            for li in tag.find_all("li", recursive=False):
                li_text = re.sub(r"\s+", " ", li.get_text(separator=" ", strip=True)).strip()
                if not li_text:
                    continue
                marker = f"{len(lines) + 1}." if tag_name == "ol" else "-"
                lines.append(f"{marker} {li_text}")
            if lines:
                elements.append(Element(type="text", content="\n".join(lines), page_num=page_num))
        elif tag_name == "blockquote":
            quoted = tag.get_text(separator="\n", strip=True)
            q_lines = [f"> {ln.strip()}" for ln in quoted.splitlines() if ln.strip()]
            if q_lines:
                elements.append(Element(type="text", content="\n".join(q_lines), page_num=page_num))
        elif tag_name in ("img", "image"):
            emit_figure(tag)
        elif tag_name in _CONTAINER_TAGS:
            for child in tag.children:
                if isinstance(child, Tag):
                    process_node(child)

    for child in body.children:
        if isinstance(child, Tag):
            process_node(child)

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
            spine_elements = _html_to_elements(
                html, page_num=i + 1, base_href=item.get_name(),
            )
            if spine_elements and all_elements:
                all_elements.append(Element(type="section_break", content="", page_num=i + 1))
            all_elements.extend(spine_elements)

        return all_elements
