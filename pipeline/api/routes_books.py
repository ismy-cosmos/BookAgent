import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException

from pipeline.api import staging
from pipeline.api.config import get_chroma_dir
from pipeline.api.import_queue import get_import_queue
from pipeline.store.chroma_store import get_store
from scripts.ingest import _load_manifest, _save_manifest, _remove_by_source_file

router = APIRouter()


def _store():
    return get_store(get_chroma_dir())


@router.get("/books")
def list_books() -> dict:
    return {"books": _store().list_books()}


@router.delete("/books/{book_id}")
def delete_book(book_id: str) -> dict:
    store = _store()
    if book_id not in store.list_books():
        raise HTTPException(status_code=404, detail=f"book_id '{book_id}' 不存在")
    if get_import_queue().book_has_pending_or_active_task(book_id):
        raise HTTPException(status_code=409, detail=f"'{book_id}' 正在导入中，暂不可删除")
    store.delete_collection(book_id)
    # 这本书名下所有落盘记录一起删，不留孤儿文件：
    # manifest、失败清单、两个缓存、待导入列表、对话历史
    manifest_dir = Path(get_chroma_dir()) / ".manifests"
    for suffix in ("json", "failures.json", "parse_cache.json", "vlm_cache.json"):
        (manifest_dir / f"{book_id}.{suffix}").unlink(missing_ok=True)
    staging.delete_list(get_chroma_dir(), book_id)
    shutil.rmtree(Path(get_chroma_dir()) / ".conversations" / book_id, ignore_errors=True)
    return {"deleted": book_id}


@router.get("/books/{book_id}/files")
def list_files(book_id: str) -> dict:
    store = _store()
    if book_id not in store.list_books():
        raise HTTPException(status_code=404, detail=f"book_id '{book_id}' 不存在")

    manifest_dir = str(Path(get_chroma_dir()) / ".manifests")
    manifest = _load_manifest(manifest_dir, book_id)
    return {"files": list(manifest["sha256_to_file"].values())}


@router.delete("/books/{book_id}/files/{source_file}")
def delete_file(book_id: str, source_file: str) -> dict:
    store = _store()
    if book_id not in store.list_books():
        raise HTTPException(status_code=404, detail=f"book_id '{book_id}' 不存在")
    if get_import_queue().book_has_pending_or_active_task(book_id):
        raise HTTPException(status_code=409, detail=f"'{book_id}' 正在导入中，暂不可删除")

    manifest_dir = str(Path(get_chroma_dir()) / ".manifests")
    manifest = _load_manifest(manifest_dir, book_id)
    updated, removed = _remove_by_source_file(manifest, source_file)
    if not removed:
        raise HTTPException(
            status_code=404,
            detail=f"文件 '{source_file}' 不在 book '{book_id}' 中",
        )

    store.delete_by_source(book_id, source_file)
    _save_manifest(manifest_dir, book_id, updated)
    return {"deleted_file": source_file, "book_id": book_id}
