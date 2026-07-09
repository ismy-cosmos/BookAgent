from __future__ import annotations
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from pipeline.api import staging
from pipeline.api.config import get_chroma_dir
from pipeline.api.import_queue import get_import_queue
from scripts.ingest import _ALL_EXTS

router = APIRouter()


class StagedFileRequest(BaseModel):
    file_path: str


class SubmitImportRequest(BaseModel):
    book_id: str


@router.get("/books/{book_id}/staged-files")
def list_staged_files(book_id: str) -> dict:
    # 不校验书是否存在：待导入列表先于 Chroma collection 存在，
    # 新书第一次导入前就要能往里加文件。
    return {"files": staging.list_files(get_chroma_dir(), book_id)}


@router.post("/books/{book_id}/staged-files")
def add_staged_file(book_id: str, req: StagedFileRequest) -> dict:
    p = Path(req.file_path)
    if not p.is_file():
        raise HTTPException(status_code=400, detail=f"文件不存在：{req.file_path}")
    if p.suffix.lower() not in _ALL_EXTS:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型：{p.suffix}")
    return {"files": staging.add_file(get_chroma_dir(), book_id, req.file_path)}


@router.delete("/books/{book_id}/staged-files")
def remove_staged_file(book_id: str, file_path: str) -> dict:
    removed = staging.remove_file(get_chroma_dir(), book_id, file_path)
    if not removed:
        raise HTTPException(status_code=404, detail=f"文件不在待导入列表中：{file_path}")
    return {"files": staging.list_files(get_chroma_dir(), book_id)}


@router.post("/books", status_code=202)
def submit_import(req: SubmitImportRequest) -> dict:
    files = staging.list_files(get_chroma_dir(), req.book_id)
    if not files:
        raise HTTPException(status_code=400, detail="待导入文件列表为空，没有可提交的内容")
    task_id = get_import_queue().enqueue(req.book_id, files)
    return {"task_id": task_id, "file_count": len(files)}


@router.get("/progress")
def progress() -> dict:
    q = get_import_queue()
    return {**q.get_status(), **q.get_progress()}


@router.post("/import/pause")
def pause_import() -> dict:
    q = get_import_queue()
    q.request_pause()
    return q.get_status()


@router.post("/import/resume")
def resume_import() -> dict:
    q = get_import_queue()
    q.resume()
    return q.get_status()


@router.post("/import/{task_id}/cancel")
def cancel_import(task_id: str) -> dict:
    if not get_import_queue().cancel(task_id):
        raise HTTPException(
            status_code=409,
            detail=f"任务 '{task_id}' 不在排队中（已开始处理、已完成或不存在），无法取消",
        )
    return {"cancelled": task_id}
