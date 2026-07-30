from __future__ import annotations
import os

from pipeline.agent.client import OllamaAgentClient
from pipeline.agent.executor import RealExecutor
from pipeline.api.config import get_chroma_dir
from pipeline.embed import Embedder
from pipeline.ollama_utils import OLLAMA_BASE_URL, ollama_openai_base_url
from pipeline.store.chroma_store import get_store

_MODEL = os.environ.get("BOOKAGENT_MODEL", "qwen3:q4km")

_embedder: Embedder | None = None
_clients: dict[str, OllamaAgentClient] = {}


def get_model_name() -> str:
    return _MODEL


def _get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = Embedder(device="cpu")
    return _embedder


def get_client(book_id: str) -> OllamaAgentClient:
    if book_id not in _clients:
        store = get_store(get_chroma_dir())
        executor = RealExecutor(book_id=book_id, embedder=_get_embedder(), store=store)
        _clients[book_id] = OllamaAgentClient(
            model=_MODEL,
            executor=executor,
            base_url=ollama_openai_base_url(OLLAMA_BASE_URL),
        )
    return _clients[book_id]


def evict_client(book_id: str) -> None:
    _clients.pop(book_id, None)


def reset_registry() -> None:
    """仅供测试用：清空缓存的 client/embedder，避免测试间互相污染。"""
    global _embedder, _clients
    _embedder = None
    _clients = {}
