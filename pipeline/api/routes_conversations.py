from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from pipeline.agent.answer import answer
from pipeline.api import busy_state
from pipeline.api import conversations as conv_store
from pipeline.api.agent_registry import get_client, get_model_name
from pipeline.api.config import get_chroma_dir
from pipeline.ollama_utils import OLLAMA_BASE_URL, ensure_model_loaded
from pipeline.store.chroma_store import get_store

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


class AskRequest(BaseModel):
    question: str


@router.post("/books/{book_id}/conversations/{conversation_id}/ask")
def ask(book_id: str, conversation_id: str, body: AskRequest) -> dict:
    conflict = busy_state.try_acquire("answering", book_id)
    if conflict is not None:
        detail = ("正在导入书籍，请稍后再问" if conflict.reason == "ingesting"
                   else "当前有其他对话正在处理中，请稍后再问")
        raise HTTPException(status_code=409, detail=detail)

    try:
        try:
            record = conv_store.load_conversation(get_chroma_dir(), book_id, conversation_id)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"对话 '{conversation_id}' 不存在")

        store = get_store(get_chroma_dir())
        if store.count(book_id) == 0:
            raise HTTPException(status_code=400, detail=f"book '{book_id}' 还没有可用内容")

        history = conv_store.history_from_record(record)
        try:
            ensure_model_loaded(OLLAMA_BASE_URL, get_model_name())
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"无法连接本地模型服务，请检查 Ollama 是否已启动（{type(e).__name__}: {e}）",
            )

        client = get_client(book_id)
        try:
            result = answer(body.question, history=history, client=client)
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"无法连接本地模型服务，请检查 Ollama 是否已启动（{type(e).__name__}: {e}）",
            )

        conv_store.append_turn(get_chroma_dir(), book_id, conversation_id, result.history[-1])

        return {
            "answer": result.answer,
            "citations": [
                {
                    "chunk_id": c.chunk_id,
                    "source_file": c.source_file,
                    "element_type": c.element_type,
                    "citation": c.citation,
                    "score": c.score,
                }
                for c in result.citations
            ],
            "triggered_tool": result.triggered_tool,
            "total_tokens": result.total_tokens,
            "latency_s": result.latency_s,
            "used_calculate": result.used_calculate,
            "attempted_retrieve": result.attempted_retrieve,
        }
    finally:
        busy_state.release()
