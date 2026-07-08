import os
from fastapi.testclient import TestClient

from pipeline.api.app import app
from pipeline.store.chroma_store import ChromaStore

client = TestClient(app)


def test_list_books_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    resp = client.get("/books")
    assert resp.status_code == 200
    assert resp.json() == {"books": []}


def test_list_books_returns_existing(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    ChromaStore(persist_dir=str(tmp_path))._collection("ostep")
    resp = client.get("/books")
    assert resp.json() == {"books": ["ostep"]}


def test_delete_book_not_found(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    resp = client.delete("/books/missing")
    assert resp.status_code == 404


def test_delete_book_removes_it(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    ChromaStore(persist_dir=str(tmp_path))._collection("ostep")
    resp = client.delete("/books/ostep")
    assert resp.status_code == 200
    assert resp.json() == {"deleted": "ostep"}
    assert client.get("/books").json() == {"books": []}
