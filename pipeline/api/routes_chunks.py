from fastapi import APIRouter, HTTPException

from pipeline.api.config import get_chroma_dir
from pipeline.store.chroma_store import get_store

router = APIRouter()


@router.get("/books/{book_id}/chunks/{chunk_id:path}")
def get_chunk(book_id: str, chunk_id: str) -> dict:
    store = get_store(get_chroma_dir())
    results = store.get(book_id, [chunk_id])
    if not results:
        raise HTTPException(status_code=404, detail=f"未找到 chunk '{chunk_id}'")
    return results[0]
