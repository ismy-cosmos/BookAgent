import json
import os
from pathlib import Path

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


def _write_manifest(chroma_dir: Path, book_id: str, sha_to_file: dict) -> None:
    manifest_dir = chroma_dir / ".manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    (manifest_dir / f"{book_id}.json").write_text(
        json.dumps({"sha256_to_file": sha_to_file})
    )


def test_list_files_not_found_book(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    resp = client.get("/books/missing/files")
    assert resp.status_code == 404


def test_list_files_empty_when_no_manifest(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    ChromaStore(persist_dir=str(tmp_path))._collection("ostep")
    resp = client.get("/books/ostep/files")
    assert resp.status_code == 200
    assert resp.json() == {"files": []}


def test_list_files_returns_manifest_values(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    ChromaStore(persist_dir=str(tmp_path))._collection("ostep")
    _write_manifest(tmp_path, "ostep", {"abc": "ch01.pdf", "def": "ch02.pdf"})
    resp = client.get("/books/ostep/files")
    assert resp.status_code == 200
    assert sorted(resp.json()["files"]) == ["ch01.pdf", "ch02.pdf"]


def test_delete_file_not_found_book(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    resp = client.delete("/books/missing/files/ch01.pdf")
    assert resp.status_code == 404


def test_delete_file_not_found_file(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    ChromaStore(persist_dir=str(tmp_path))._collection("ostep")
    _write_manifest(tmp_path, "ostep", {"abc": "ch01.pdf"})
    resp = client.delete("/books/ostep/files/missing.pdf")
    assert resp.status_code == 404


def test_delete_file_removes_manifest_entry(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    ChromaStore(persist_dir=str(tmp_path))._collection("ostep")
    _write_manifest(tmp_path, "ostep", {"abc": "ch01.pdf", "def": "ch02.pdf"})

    resp = client.delete("/books/ostep/files/ch01.pdf")

    assert resp.status_code == 200
    assert resp.json() == {"deleted_file": "ch01.pdf", "book_id": "ostep"}
    manifest = json.loads((tmp_path / ".manifests" / "ostep.json").read_text())
    assert manifest == {"sha256_to_file": {"def": "ch02.pdf"}}
