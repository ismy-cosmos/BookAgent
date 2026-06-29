from __future__ import annotations
import re
from pathlib import Path
from typing import Optional

import tiktoken

from pipeline.parse.base import Element
from .schema import Chunk

_MAX_TOKENS = 512
_OVERLAP_TOKENS = 50
_ATOMIC_TYPES = {"table", "formula", "code", "figure"}
_ENC = None


def _get_enc():
    global _ENC
    if _ENC is None:
        _ENC = tiktoken.get_encoding("cl100k_base")
    return _ENC


def _token_count(text: str) -> int:
    return len(_get_enc().encode(text))


def _last_n_tokens(text: str, n: int) -> str:
    enc = _get_enc()
    ids = enc.encode(text)
    return enc.decode(ids[-n:]) if len(ids) >= n else text


def _split_at_sentence(text: str, max_tokens: int) -> list[str]:
    if _token_count(text) <= max_tokens:
        return [text]

    # 第一级：句子边界（英文需要后跟空格，中文不需要）
    sentences = re.split(r'(?<=[.!?])\s+|(?<=[。！？])', text)
    sentences = [s for s in sentences if s.strip()]

    # 第二级：单句超限时按空格分词
    result: list[str] = []
    for sent in sentences:
        if _token_count(sent) <= max_tokens:
            result.append(sent)
        else:
            words = sent.split()
            buf: list[str] = []
            buf_tok = 0
            for w in words:
                wt = _token_count(w)
                if buf and buf_tok + wt > max_tokens:
                    result.append(' '.join(buf))
                    buf, buf_tok = [w], wt
                else:
                    buf.append(w)
                    buf_tok += wt
            if buf:
                result.append(' '.join(buf))

    # 第三级：单词级仍超限（长URL无空格）→ 按 token 强制截断
    enc = _get_enc()
    final: list[str] = []
    for part in result:
        ids = enc.encode(part)
        if len(ids) <= max_tokens:
            final.append(part)
        else:
            for i in range(0, len(ids), max_tokens):
                final.append(enc.decode(ids[i : i + max_tokens]))

    return final or [text]


def _make_chunk_id(book_id: str, source_stem: str, page_start: Optional[int], seq: int) -> str:
    page_str = f"p{page_start:04d}" if page_start is not None else "pNone"
    return f"{book_id}/{source_stem}/{page_str}/{seq:04d}"


class Chunker:
    def __init__(self, max_tokens: int = _MAX_TOKENS, overlap_tokens: int = _OVERLAP_TOKENS):
        self._max_tokens = max_tokens
        self._overlap_tokens = overlap_tokens

    def chunk(
        self,
        elements: list[Element],
        book_id: str,
        source_file: str,
        seq_offset: int = 0,
    ) -> list[Chunk]:
        source_stem = Path(source_file).stem
        chunks: list[Chunk] = []
        buf: list[Element] = []
        buf_tok = 0
        overlap_text = ""
        seq = seq_offset

        def _page_start(elems: list[Element]) -> Optional[int]:
            if not elems:
                return None
            pn = elems[0].page_num
            return pn if pn != 0 else None

        def _emit(elems: list[Element], etype: str, extra_content: str = "") -> None:
            nonlocal seq
            raw = " ".join(e.content for e in elems) if elems else extra_content
            content = (overlap_text + raw).strip() if overlap_text else raw.strip()
            if not content:
                return
            tc = _token_count(content)
            ps = _page_start(elems)
            chunks.append(Chunk(
                chunk_id=_make_chunk_id(book_id, source_stem, ps, seq),
                book_id=book_id,
                source_file=source_file,
                element_type=etype,
                content=content,
                token_count=tc,
                page_start=ps,
            ))
            seq += 1

        def flush(carry_overlap: bool) -> None:
            nonlocal buf, buf_tok, overlap_text
            if not buf:
                return
            _emit(buf, "text")
            if carry_overlap:
                last = chunks[-1].content
                overlap_text = _last_n_tokens(last, self._overlap_tokens) + " "
            else:
                overlap_text = ""
            buf = []
            buf_tok = 0

        for elem in elements:
            is_heading = (
                elem.type == "text"
                and elem.content.strip().startswith("#")
            )
            is_boundary = is_heading or elem.type == "section_break"
            is_atomic = elem.type in _ATOMIC_TYPES

            if is_boundary:
                flush(carry_overlap=False)
                continue

            if is_atomic:
                flush(carry_overlap=True)
                _emit([], etype=elem.type, extra_content=elem.content)
                # atomic chunks don't carry overlap forward
                overlap_text = ""
                continue

            # Regular text element
            elem_tok = _token_count(elem.content)
            if elem_tok > self._max_tokens:
                # Long element: flush buffer (carry overlap), then split element itself
                flush(carry_overlap=True)
                for part in _split_at_sentence(elem.content, self._max_tokens):
                    part_elem = Element(type=elem.type, content=part, page_num=elem.page_num)
                    _emit([part_elem], "text")
                    overlap_text = _last_n_tokens(part, self._overlap_tokens) + " "
                continue

            if buf and buf_tok + elem_tok > self._max_tokens:
                flush(carry_overlap=True)

            buf.append(elem)
            buf_tok += elem_tok

        flush(carry_overlap=False)
        return chunks
