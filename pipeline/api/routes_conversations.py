from fastapi import APIRouter, HTTPException

from pipeline.api import conversations as conv_store
from pipeline.api.config import get_chroma_dir

router = APIRouter()


@router.get("/books/{book_id}/conversations")
def list_conversations(book_id: str) -> dict:
    return {"conversations": conv_store.list_conversations(get_chroma_dir(), book_id)}


@router.post("/books/{book_id}/conversations")
def create_conversation(book_id: str) -> dict:
    return conv_store.create_conversation(get_chroma_dir(), book_id)


@router.get("/books/{book_id}/conversations/{conversation_id}")
def get_conversation(book_id: str, conversation_id: str) -> dict:
    try:
        return conv_store.load_conversation(get_chroma_dir(), book_id, conversation_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"对话 '{conversation_id}' 不存在")


@router.delete("/books/{book_id}/conversations/{conversation_id}")
def delete_conversation(book_id: str, conversation_id: str) -> dict:
    try:
        conv_store.delete_conversation(get_chroma_dir(), book_id, conversation_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"对话 '{conversation_id}' 不存在")
    return {"deleted": conversation_id}
