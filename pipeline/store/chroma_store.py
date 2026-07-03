from __future__ import annotations
import os

import chromadb

from pipeline.chunk.schema import Chunk

_CHROMA_DIR = os.environ.get("CHROMA_DIR", ".chroma")


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
            name=book_id,
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

    def count(self, book_id: str) -> int:
        return self._collection(book_id).count()
