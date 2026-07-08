from fastapi import APIRouter, HTTPException

from pipeline.api.config import get_chroma_dir
from pipeline.store.chroma_store import ChromaStore

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
    store.delete_collection(book_id)
    return {"deleted": book_id}
