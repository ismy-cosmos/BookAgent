from fastapi.testclient import TestClient

from pipeline.api.app import app
from pipeline.chunk.schema import Chunk
from pipeline.store.chroma_store import ChromaStore

client = TestClient(app)


def _make_one_chunk() -> list[Chunk]:
    return [Chunk(
        chunk_id="c1", book_id="ostep", source_file="ch3.pdf",
        element_type="text", content="fork() 相关内容", token_count=10,
        page_start=42, page_end=42, start_sec=None, end_sec=None, low_confidence=False,
    )]


def test_get_chunk_not_found(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    ChromaStore(persist_dir=str(tmp_path))._collection("ostep")
    resp = client.get("/books/ostep/chunks/does-not-exist")
    assert resp.status_code == 404


def test_get_chunk_returns_content_and_location(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    store = ChromaStore(persist_dir=str(tmp_path))
    store.add_chunks("ostep", _make_one_chunk(), embeddings=[[0.0] * 8])

    resp = client.get("/books/ostep/chunks/c1")

    assert resp.status_code == 200
    body = resp.json()
    assert body["content"] == "fork() 相关内容"
    assert body["source_file"] == "ch3.pdf"
    assert body["page_start"] == 42
    assert body["page_end"] == 42
