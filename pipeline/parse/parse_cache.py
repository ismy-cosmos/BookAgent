"""阶段1解析结果缓存：键是文件整体字节的 sha256，值是这个文件解析出的
Element 列表（PDF/EPUB/独立图片）或 Chunk 列表（音频），跟 `_PendingFile`
"elements 或 chunks 二选一"的结构对应。用于用户暂停后重新提交同一批文件、
或上次运行部分失败后重试时，跳过已经跑过 GPU 的解析工作（marker/surya
或 WhisperX）。

纯优化——缓存文件损坏、缺失、或读写出错，一律静默退化为"当作未命中"，
不影响正确性，也不会让调用方的批次因此失败。
"""
from __future__ import annotations
import base64
import json
from dataclasses import asdict
from pathlib import Path

from pipeline.chunk.schema import Chunk
from pipeline.parse.base import Element


def _cache_path(chroma_dir: str, book_id: str) -> Path:
    return Path(chroma_dir) / ".manifests" / f"{book_id}.parse_cache.json"


def _load_all(chroma_dir: str, book_id: str) -> dict:
    p = _cache_path(chroma_dir, book_id)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save_all(chroma_dir: str, book_id: str, data: dict) -> None:
    p = _cache_path(chroma_dir, book_id)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(json.dumps(data))
        tmp.replace(p)
    except OSError as e:
        print(f"[warn] 解析结果缓存写入失败（不影响正确性，仅本次不省这份工作）: {e}")


def _encode_element(elem: Element) -> dict:
    d = asdict(elem)
    image_bytes = d["metadata"].get("image_bytes")
    if isinstance(image_bytes, (bytes, bytearray)):
        d["metadata"]["image_bytes"] = {
            "__bytes_b64__": base64.b64encode(image_bytes).decode("ascii")
        }
    return d


def _decode_element(d: dict) -> Element:
    metadata = dict(d["metadata"])
    image_bytes = metadata.get("image_bytes")
    if isinstance(image_bytes, dict) and "__bytes_b64__" in image_bytes:
        metadata["image_bytes"] = base64.b64decode(image_bytes["__bytes_b64__"])
    return Element(type=d["type"], content=d["content"], page_num=d["page_num"],
                   metadata=metadata)


def get(
    chroma_dir: str, book_id: str, file_sha: str,
) -> tuple[list[Element] | None, list[Chunk] | None] | None:
    data = _load_all(chroma_dir, book_id)
    entry = data.get(file_sha)
    if entry is None:
        return None
    try:
        elements = ([_decode_element(e) for e in entry["elements"]]
                    if entry.get("elements") is not None else None)
        chunks = ([Chunk(**c) for c in entry["chunks"]]
                  if entry.get("chunks") is not None else None)
    except Exception:
        # 条目损坏（缺字段、坏 base64、字段类型不对……）一律当未命中
        return None
    return elements, chunks


def set(
    chroma_dir: str,
    book_id: str,
    file_sha: str,
    elements: list[Element] | None,
    chunks: list[Chunk] | None,
) -> None:
    try:
        entry = {
            "elements": [_encode_element(e) for e in elements] if elements is not None else None,
            "chunks": [asdict(c) for c in chunks] if chunks is not None else None,
        }
    except Exception as e:
        print(f"[warn] 解析结果缓存编码失败（不影响正确性，仅本次不省这份工作）: {e}")
        return
    data = _load_all(chroma_dir, book_id)
    data[file_sha] = entry
    _save_all(chroma_dir, book_id, data)


def delete(chroma_dir: str, book_id: str, file_sha: str) -> None:
    data = _load_all(chroma_dir, book_id)
    if file_sha in data:
        del data[file_sha]
        _save_all(chroma_dir, book_id, data)


def keys(chroma_dir: str, book_id: str) -> list[str]:
    return list(_load_all(chroma_dir, book_id).keys())
