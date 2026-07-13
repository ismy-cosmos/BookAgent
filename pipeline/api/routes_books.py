import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from pipeline.api import agent_registry, conversations as conv_store, staging
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
    # 忙碌检查必须排在"书存不存在"前面：一本书第一次导入、还没跑到阶段3
    # 之前，collection 根本没被建出来（见 scripts/ingest.py 的 _store_file），
    # 此时 store.list_books() 查不到它——如果先查存在，会被 404 抢跑，
    # 忙碌检查永远轮不到，导致"正在导入的全新书"能被绕过保护直接删除。
    if get_import_queue().book_has_pending_or_active_task(book_id):
        raise HTTPException(status_code=409, detail=f"'{book_id}' 正在导入中，暂不可删除")
    store = _store()
    if book_id not in store.list_books():
        raise HTTPException(status_code=404, detail=f"book_id '{book_id}' 不存在")
    store.delete_collection(book_id)
    # 这本书名下所有落盘记录一起删，不留孤儿文件：
    # manifest、失败清单、两个缓存、待导入列表、对话历史
    manifest_dir = Path(get_chroma_dir()) / ".manifests"
    for suffix in ("json", "failures.json", "parse_cache.json", "vlm_cache.json"):
        (manifest_dir / f"{book_id}.{suffix}").unlink(missing_ok=True)
    staging.delete_list(get_chroma_dir(), book_id)
    shutil.rmtree(Path(get_chroma_dir()) / ".conversations" / book_id, ignore_errors=True)
    return {"deleted": book_id}


class RenameBookRequest(BaseModel):
    new_book_id: str


@router.patch("/books/{book_id}")
def rename_book(book_id: str, body: RenameBookRequest) -> dict:
    # 顺序原因同 delete_book：忙碌检查要排在"书存不存在"前面，否则一本
    # 正在第一次导入、collection 还没建出来的书会被 404 抢跑。
    if get_import_queue().book_has_pending_or_active_task(book_id):
        raise HTTPException(status_code=409, detail=f"'{book_id}' 正在导入中，暂不可改名")
    store = _store()
    if book_id not in store.list_books():
        raise HTTPException(status_code=404, detail=f"book_id '{book_id}' 不存在")
    new_id = body.new_book_id
    if new_id in store.list_books():
        raise HTTPException(status_code=409, detail=f"book_id '{new_id}' 已存在")

    store.rename_collection(book_id, new_id)

    manifest_dir = Path(get_chroma_dir()) / ".manifests"
    for suffix in ("json", "failures.json", "parse_cache.json", "vlm_cache.json"):
        old_path = manifest_dir / f"{book_id}.{suffix}"
        if old_path.exists():
            old_path.rename(manifest_dir / f"{new_id}.{suffix}")
    staging.rename_list(get_chroma_dir(), book_id, new_id)
    conv_store.rename_book(get_chroma_dir(), book_id, new_id)
    agent_registry.evict_client(book_id)

    return {"book_id": new_id}


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
    # 顺序原因同 delete_book：忙碌检查要排在"书存不存在"前面。这条目前
    # 前端摸不到（FileList 依赖 list_files，同样先查存在，书没建出来时
    # 文件列表本身就是空的/404，渲染不出可点的删除按钮）——但后端不能靠
    # "现在没有调用方能触发"来决定要不要防护，必须自己保证正确。
    if get_import_queue().book_has_pending_or_active_task(book_id):
        raise HTTPException(status_code=409, detail=f"'{book_id}' 正在导入中，暂不可删除")
    store = _store()
    if book_id not in store.list_books():
        raise HTTPException(status_code=404, detail=f"book_id '{book_id}' 不存在")

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
