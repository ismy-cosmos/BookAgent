from pathlib import Path

from fastapi import APIRouter, HTTPException

from pipeline.api.config import get_chroma_dir
from pipeline.api.import_queue import get_import_queue
from pipeline.store.chroma_store import ChromaStore
from scripts.ingest import _load_manifest, _save_manifest, _remove_by_source_file

router = APIRouter()


def _store() -> ChromaStore:
    return ChromaStore(persist_dir=get_chroma_dir())


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
