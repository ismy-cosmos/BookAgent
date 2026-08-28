"""每本书的"待导入文件列表"——用户草稿态的文件清单，独立于 ImportQueue
内存里的任务，落盘持久化、跨应用重启保留。它是导入的唯一入口：提交那一刻
的列表内容决定这次任务处理哪些文件。

与 parse_cache/vlm_cache 不同，这份列表是正确性入口而非优化——写入失败
必须向上抛（HTTP 层转 500），不能静默退化。读取时文件损坏退化为空列表
（草稿态数据，用户可重新添加，且原子写保证正常断电不会产生半截文件）。
"""
from __future__ import annotations
import json
from pathlib import Path


def _list_path(chroma_dir: str, book_id: str) -> Path:
    return Path(chroma_dir) / ".manifests" / f"{book_id}.pending_files.json"


def list_files(chroma_dir: str, book_id: str) -> list[str]:
    p = _list_path(chroma_dir, book_id)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return []
    return data if isinstance(data, list) else []


def _save(chroma_dir: str, book_id: str, files: list[str]) -> None:
    p = _list_path(chroma_dir, book_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(files, ensure_ascii=False, indent=2))
    tmp.replace(p)


def add_file(chroma_dir: str, book_id: str, file_path: str) -> list[str]:
    files = list_files(chroma_dir, book_id)
    if file_path not in files:
        files.append(file_path)
        _save(chroma_dir, book_id, files)
    return files


def remove_file(chroma_dir: str, book_id: str, file_path: str) -> bool:
    files = list_files(chroma_dir, book_id)
    if file_path not in files:
        return False
    files.remove(file_path)
    _save(chroma_dir, book_id, files)
    return True


def delete_list(chroma_dir: str, book_id: str) -> None:
    _list_path(chroma_dir, book_id).unlink(missing_ok=True)


def rename_list(chroma_dir: str, old_book_id: str, new_book_id: str) -> None:
    old_path = _list_path(chroma_dir, old_book_id)
    if old_path.exists():
        old_path.rename(_list_path(chroma_dir, new_book_id))
