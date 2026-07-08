"""阶段2 VLM 描述缓存：键是缩放后图片字节的 sha256，值是描述文本。
图片是从源文件确定性解析出来的、缩放函数也是确定性的，同一份源文件
重新解析多少次抠出来的字节都一样，键稳定；跟 parse_cache 存的是同一个
缩放后版本，两边不会各算一次 sha 对不上。

纯优化——语义和失败退化策略跟 parse_cache 完全对称。
"""
from __future__ import annotations
import json
from pathlib import Path


def _cache_path(chroma_dir: str, book_id: str) -> Path:
    return Path(chroma_dir) / ".manifests" / f"{book_id}.vlm_cache.json"


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
        print(f"[warn] VLM 描述缓存写入失败（不影响正确性，仅本次不省这份工作）: {e}")


def get(chroma_dir: str, book_id: str, image_sha: str) -> str | None:
    return _load_all(chroma_dir, book_id).get(image_sha)


def set(chroma_dir: str, book_id: str, image_sha: str, description: str) -> None:
    data = _load_all(chroma_dir, book_id)
    data[image_sha] = description
    _save_all(chroma_dir, book_id, data)


def delete(chroma_dir: str, book_id: str, image_sha: str) -> None:
    data = _load_all(chroma_dir, book_id)
    if image_sha in data:
        del data[image_sha]
        _save_all(chroma_dir, book_id, data)
