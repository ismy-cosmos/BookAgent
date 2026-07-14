from __future__ import annotations
import os
import threading

import chromadb

from pipeline.chunk.schema import Chunk

_CHROMA_DIR = os.environ.get("CHROMA_DIR", ".chroma")

_COLLECTION_PREFIX = "b_"


def _encode_collection_name(book_id: str) -> str:
    """book_id 可以是任意用户输入（中文、空格、1-2 个字符……），但 Chroma
    collection name 只认 3-512 个 [a-zA-Z0-9._-]、首尾字母数字。统一转成
    十六进制可以绕开所有这些限制，不用为"本来就合法的名字"开例外分支。"""
    return _COLLECTION_PREFIX + book_id.encode("utf-8").hex()


def _decode_collection_name(name: str) -> str:
    return bytes.fromhex(name[len(_COLLECTION_PREFIX):]).decode("utf-8")


def _meta_val(v):
    """Chroma metadata must be str|int|float|bool. Convert None → ''."""
    return v if v is not None else ""


def _from_meta_val(v):
    """Restore '' → None for optional numeric fields."""
    return None if v == "" else v


class ChromaStore:
    def __init__(self, persist_dir: str = _CHROMA_DIR):
        self._client = chromadb.PersistentClient(path=persist_dir)

    def _collection(self, book_id: str):
        return self._client.get_or_create_collection(
            name=_encode_collection_name(book_id),
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(
        self,
        book_id: str,
        chunks: list[Chunk],
        embeddings: list[list[float]],
    ) -> None:
        col = self._collection(book_id)
        col.add(
            ids=[c.chunk_id for c in chunks],
            embeddings=embeddings,
            documents=[c.content for c in chunks],
            metadatas=[
                {
                    "book_id": c.book_id,
                    "source_file": c.source_file,
                    "element_type": c.element_type,
                    "token_count": c.token_count,
                    "page_start": _meta_val(c.page_start),
                    "page_end": _meta_val(c.page_end),
                    "start_sec": _meta_val(c.start_sec),
                    "end_sec": _meta_val(c.end_sec),
                    "low_confidence": c.low_confidence,
                }
                for c in chunks
            ],
        )

    def delete_by_source(self, book_id: str, source_file: str) -> None:
        self._collection(book_id).delete(where={"source_file": source_file})

    def query(
        self,
        book_id: str,
        query_embedding: list[float],
        n_results: int = 5,
    ) -> list[dict]:
        col = self._collection(book_id)
        raw = col.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "distances", "metadatas"],
        )
        results = []
        for chunk_id, doc, dist, meta in zip(
            raw["ids"][0],
            raw["documents"][0],
            raw["distances"][0],
            raw["metadatas"][0],
        ):
            results.append({
                "chunk_id": chunk_id,
                "content": doc,
                "score": dist,
                "source_file": meta.get("source_file"),
                "element_type": meta.get("element_type"),
                "page_start": _from_meta_val(meta.get("page_start")),
                "page_end": _from_meta_val(meta.get("page_end")),
                "start_sec": _from_meta_val(meta.get("start_sec")),
                "end_sec": _from_meta_val(meta.get("end_sec")),
                "low_confidence": meta.get("low_confidence", False),
            })
        return results

    def get(self, book_id: str, chunk_ids: list[str]) -> list[dict]:
        col = self._collection(book_id)
        raw = col.get(ids=chunk_ids, include=["documents", "metadatas"])
        results = []
        for chunk_id, doc, meta in zip(raw["ids"], raw["documents"], raw["metadatas"]):
            results.append({
                "chunk_id": chunk_id,
                "content": doc,
                "source_file": meta.get("source_file"),
                "element_type": meta.get("element_type"),
                "page_start": _from_meta_val(meta.get("page_start")),
                "page_end": _from_meta_val(meta.get("page_end")),
                "start_sec": _from_meta_val(meta.get("start_sec")),
                "end_sec": _from_meta_val(meta.get("end_sec")),
                "low_confidence": meta.get("low_confidence", False),
            })
        return results

    def count(self, book_id: str) -> int:
        return self._collection(book_id).count()

    def list_books(self) -> list[str]:
        return [_decode_collection_name(c.name) for c in self._client.list_collections()]

    def delete_collection(self, book_id: str) -> None:
        self._client.delete_collection(name=_encode_collection_name(book_id))

    def rename_collection(self, book_id: str, new_book_id: str) -> None:
        self._collection(book_id).modify(name=_encode_collection_name(new_book_id))


# 按 persist_dir 缓存：并发创建同路径的 PersistentClient 会破坏 chromadb 内部
# 的 SharedSystemClient 注册表。lru_cache 的锁只护住查/写缓存两步，构造对象
# 那一步是在锁外面跑的，并发下照样会重复构造——所以这里手写锁整段锁住。
_store_lock = threading.Lock()
_stores: dict[str, ChromaStore] = {}


def get_store(persist_dir: str = _CHROMA_DIR) -> ChromaStore:
    with _store_lock:
        if persist_dir not in _stores:
            _stores[persist_dir] = ChromaStore(persist_dir=persist_dir)
        return _stores[persist_dir]


def reset_store_cache() -> None:
    """仅供测试用：清空缓存，避免测试间互相污染。"""
    with _store_lock:
        _stores.clear()
