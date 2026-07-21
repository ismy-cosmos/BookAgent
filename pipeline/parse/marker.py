from __future__ import annotations
import io
import re
import tempfile
from pathlib import Path
from typing import Callable

import pypdfium2 as pdfium

from .base import Element, Parser

# 自定义分隔符，不用 marker 默认的 "-"*48——真实数据实测发现宽表格自己的
# 表头分隔行也是一长串短横线，会跟默认分隔符碰撞，导致 markdown 被误切、
# 页码从碰撞点起系统性漂移（详见 threads-intro.pdf 真实案例）。这个值同时
# 是测试用假分页 markdown 时的 fallback 分隔符。
_PAGE_SEP = "@@BOOKAGENT_PAGE_BREAK@@"


def _pdf_page_count(pdf_path: str) -> int:
    """轻量页数读取，不涉及 OCR/layout 模型，用于判断是否需要分批。"""
    doc = pdfium.PdfDocument(pdf_path)
    try:
        return len(doc)
    finally:
        doc.close()


def _write_page_range_pdf(pdf_path: str, start: int, end: int, dest_path: str) -> None:
    """把 pdf_path 的 [start, end) 页（0-indexed 半开区间）物理切出，
    写成一份独立的 PDF 到 dest_path。"""
    src = pdfium.PdfDocument(pdf_path)
    dst = pdfium.PdfDocument.new()
    try:
        dst.import_pages(src, list(range(start, end)))
        with open(dest_path, "wb") as f:
            dst.save(f)
    finally:
        dst.close()
        src.close()


class MarkerParser(Parser):
    """Marker-pdf parser adapter (v1.x PdfConverter API).

    Model weights are loaded once at class level and reused across instances.
    """

    _converter = None
    _page_sep = None

    @classmethod
    def _get_converter(cls):
        if cls._converter is None:
            from marker.converters.pdf import PdfConverter
            from marker.models import create_model_dict
            cls._converter = PdfConverter(
                artifact_dict=create_model_dict(),
                config={"paginate_output": True, "page_separator": _PAGE_SEP},
            )
            # Read the separator marker actually resolves/uses, rather than
            # assuming it matches our own guess — avoids silently breaking
            # page numbering if marker-pdf ever changes its default.
            resolved_renderer = cls._converter.resolve_dependencies(cls._converter.renderer)
            cls._page_sep = resolved_renderer.page_separator
        return cls._converter

    @classmethod
    def release_models(cls) -> None:
        """卸载缓存的 PdfConverter（layout/OCR 权重）并清空 CUDA 缓存。
        ingest 在 VLM 批量阶段前调用——8GB 卡装不下 marker 模型残留
        与 Ollama VLM 同时驻留。下次 parse() 会重新懒加载。"""
        if cls._converter is None:
            cls._page_sep = None
            return
        cls._converter = None
        cls._page_sep = None
        import gc
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass

    def parse(self, pdf_path: str) -> list[Element]:
        converter = self._get_converter()
        rendered = converter(pdf_path)
        return _rendered_to_elements(rendered, page_sep=self._page_sep)


def _rendered_to_elements(rendered, page_sep: str) -> list[Element]:
    """Convert a paginated MarkdownOutput to Element list.

    With paginate_output=True, MarkdownRenderer inserts page_sep between
    pages, producing sections[0] (pre-page artifact), sections[1] (page 1),
    sections[2] (page 2), …  page_num = section index (1-based).

    page_sep must be the separator the renderer actually used (see
    MarkerParser._get_converter) — never assume a hardcoded value.
    """
    markdown = getattr(rendered, "markdown", "") or ""
    if not markdown.strip():
        return []

    sections = markdown.split(page_sep)
    # sections[0] is always a pre-page artifact ({0} or empty); skip it.
    # sections[i] (i >= 1) is the content of page i.
    elements: list[Element] = []
    for i, section in enumerate(sections[1:], start=1):
        # Strip the trailing \n\n{N} left by marker's paginate_output format:
        # each page div is rendered as "{page_id}[sep]\n\ncontent", so after
        # splitting on [sep] the next page's {N} sticks to the end of this
        # section. It's a pagination artifact, not document content.
        section = re.sub(r"\n\n\{\d+\}\s*$", "", section)
        elements.extend(_markdown_to_elements(section, page_num=i))

    images = getattr(rendered, "images", None)
    if isinstance(images, dict) and images:
        for elem in elements:
            if elem.type != "figure":
                continue
            m = re.match(r"^!\[[^\]]*\]\(([^)]+)\)", elem.content)
            if not m:
                continue
            pil_img = images.get(m.group(1))
            if pil_img is None:
                continue
            buf = io.BytesIO()
            try:
                pil_img.save(buf, format="PNG")
            except Exception:
                try:
                    pil_img.convert("RGB").save(buf, format="PNG")
                except Exception:
                    continue  # 尽力而为：转码失败则维持占位符现状
            elem.metadata["image_bytes"] = buf.getvalue()

    return elements


def _split_markdown_blocks(markdown: str) -> list[str]:
    """Split markdown into top-level blocks on blank lines.

    Fenced code blocks (```...```) and standalone ``$$`` math blocks are
    treated as atomic: blank lines *inside* them do not split the block,
    since multi-statement code listings and multi-line formulas commonly
    contain blank lines of their own.
    """
    lines = markdown.strip("\n").split("\n")
    blocks: list[str] = []
    buf: list[str] = []
    in_fence = False
    in_math = False

    def flush():
        if buf:
            text = "\n".join(buf).strip("\n")
            if text.strip():
                blocks.append(text)
            buf.clear()

    for line in lines:
        stripped = line.strip()

        if in_fence:
            buf.append(line)
            if stripped.startswith("```"):
                in_fence = False
                flush()
            continue

        if in_math:
            buf.append(line)
            if stripped == "$$":
                in_math = False
                flush()
            continue

        if stripped.startswith("```"):
            flush()
            in_fence = True
            buf.append(line)
            continue

        if stripped == "$$":
            flush()
            in_math = True
            buf.append(line)
            continue

        if stripped == "":
            flush()
            continue

        buf.append(line)

    flush()
    return blocks


def _markdown_to_elements(markdown: str, page_num: int) -> list[Element]:
    """Split a markdown string into typed Elements, one per block."""
    elements: list[Element] = []
    for block in _split_markdown_blocks(markdown):
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
