from __future__ import annotations
import re
from pathlib import Path
from typing import Optional

import tiktoken

from pipeline.parse.base import Element
from .schema import Chunk

_MAX_TOKENS = 512  # 不含 overlap 前缀的目标 token 上限
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


def _last_complete_sentences(text: str, max_tokens: int) -> str:
    """Return trailing complete sentences of text that fit within max_tokens.
    Falls back to _last_n_tokens if no single sentence fits."""
    sentences = re.split(r'(?<=[.!?])\s+|(?<=[。！？])', text)
    sentences = [s for s in sentences if s.strip()]
    result: list[str] = []
    total = 0
    for sent in reversed(sentences):
        t = _token_count(sent)
        if total + t <= max_tokens:
            result.insert(0, sent)
            total += t
        else:
            break
    return ' '.join(result) if result else _last_n_tokens(text, max_tokens)


def _split_at_sentence(text: str, max_tokens: int) -> list[str]:
    if _token_count(text) <= max_tokens:
        return [text]

    # 第一级：句子边界。lookahead (?=[A-Z\d一-鿿]) 要求切分点后是大写/数字/中文，
    # 避免 "e.g. " 这类缩写词被误判为句子结尾（其后跟小写字母）。
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z\d])|(?<=[。！？])', text)
    sentences = [s for s in sentences if s.strip()]

    # 贪心打包：将短句累积到接近 max_tokens 再 flush，而非每句单独成片。
    packed: list[str] = []
    buf: list[str] = []
    buf_tok = 0
    for sent in sentences:
        st = _token_count(sent)
        if buf and buf_tok + st > max_tokens:
            packed.append(' '.join(buf))
            buf, buf_tok = [sent], st
        else:
            buf.append(sent)
            buf_tok += st
    if buf:
        packed.append(' '.join(buf))

    # 第二级：packed 片段仍超限时按空格分词
    result: list[str] = []
    for piece in packed:
        if _token_count(piece) <= max_tokens:
            result.append(piece)
        else:
            words = piece.split()
            buf2: list[str] = []
            buf2_tok = 0
            for w in words:
                wt = _token_count(w)
                if buf2 and buf2_tok + wt > max_tokens:
                    result.append(' '.join(buf2))
                    buf2, buf2_tok = [w], wt
                else:
                    buf2.append(w)
                    buf2_tok += wt
            if buf2:
                result.append(' '.join(buf2))

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

        def _page_end(elems: list[Element]) -> Optional[int]:
            if not elems:
                return None
            pn = elems[-1].page_num
            return pn if pn != 0 else None

        def _emit(elems: list[Element], etype: str, content: str = "", overlap: str = "") -> None:
            nonlocal seq
            raw = content if content else (" ".join(e.content for e in elems) if elems else "")
            text = (overlap + raw).strip() if overlap else raw.strip()
            if not text:
                return
            tc = _token_count(text)
            ps = _page_start(elems)
            pe = _page_end(elems)
            chunks.append(Chunk(
                chunk_id=_make_chunk_id(book_id, source_stem, ps, seq),
                book_id=book_id,
                source_file=source_file,
                element_type=etype,
                content=text,
                token_count=tc,
                page_start=ps,
                page_end=pe,
            ))
            seq += 1

        def flush() -> None:
            nonlocal buf, buf_tok, overlap_text
            if not buf:
                return
            _emit(buf, "text", overlap=overlap_text)
            overlap_text = ""
            buf = []
            buf_tok = 0

        for elem in elements:
            is_heading = (
                elem.type == "text"
                and bool(re.match(r"#{1,6}\s", elem.content.strip()))
            )
            is_boundary = is_heading or elem.type == "section_break"
            is_atomic = elem.type in _ATOMIC_TYPES

            if is_boundary:
                flush()
                continue

            if is_atomic:
                flush()
                _emit([elem], etype=elem.type)
                overlap_text = ""
                continue

            # Regular text element
            elem_tok = _token_count(elem.content)
            if elem_tok > self._max_tokens:
                flush()
                split_target = max(1, self._max_tokens - self._overlap_tokens)
                piece_overlap = ""
                for part in _split_at_sentence(elem.content, split_target):
                    part_elem = Element(type=elem.type, content=part, page_num=elem.page_num)
                    _emit([part_elem], "text", overlap=piece_overlap)
                    piece_overlap = _last_complete_sentences(part, self._overlap_tokens) + " "
                overlap_text = ""
                continue

            if buf and buf_tok + elem_tok > self._max_tokens:
                flush()

            buf.append(elem)
            buf_tok += elem_tok

        flush()
        return chunks
