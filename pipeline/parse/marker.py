from __future__ import annotations
import re

from .base import Element, Parser


class MarkerParser(Parser):
    """Marker-pdf parser adapter (v1.x PdfConverter API).

    Model weights are loaded once at class level and reused across instances.
    """

    _converter = None

    @classmethod
    def _get_converter(cls):
        if cls._converter is None:
            from marker.converters.pdf import PdfConverter
            from marker.models import create_model_dict
            cls._converter = PdfConverter(artifact_dict=create_model_dict())
        return cls._converter

    def parse(self, pdf_path: str) -> list[Element]:
        converter = self._get_converter()
        rendered = converter(pdf_path)
        return _rendered_to_elements(rendered)


def _rendered_to_elements(rendered) -> list[Element]:
    """Convert a RenderedDocument to Element list.

    Uses per-page children when available (page_num = page_id + 1).
    Falls back to full-document markdown with page_num=0 (unknown).
    """
    children = getattr(rendered, "children", None)
    if children:
        elements: list[Element] = []
        for page_obj in children:
            page_num = getattr(page_obj, "page_id", 0) + 1
            page_md = getattr(page_obj, "markdown", "") or ""
            elements.extend(_markdown_to_elements(page_md, page_num))
        return elements

    return _markdown_to_elements(getattr(rendered, "markdown", "") or "", page_num=0)


def _markdown_to_elements(markdown: str, page_num: int) -> list[Element]:
    """Split a markdown string into typed Elements, one per block."""
    elements: list[Element] = []
    for block in re.split(r"\n{2,}", markdown.strip()):
        block = block.strip()
        if not block:
            continue
        etype, content = _classify_block(block)
        if content:
            elements.append(Element(type=etype, content=content, page_num=page_num))
    return elements


def _classify_block(block: str) -> tuple[str, str]:
    # Fenced code block
    if block.startswith("```"):
        inner = re.sub(r"^```[^\n]*\n?", "", block)
        inner = re.sub(r"\n?```$", "", inner)
        return "code", inner.strip()

    # Block-level formula: $$...$$ wrapping the whole block
    if block.startswith("$$") and block.endswith("$$") and len(block) > 4:
        return "formula", block[2:-2].strip()

    # Table: at least one pipe-delimited row
    if any(re.match(r"^\|.+\|$", ln.strip()) for ln in block.splitlines()):
        return "table", block

    # Figure: markdown image reference
    if re.match(r"^!\[", block):
        return "figure", block

    # Headings and paragraphs both → text (heading level preserved in content)
    return "text", block
