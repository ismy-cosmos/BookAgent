import json
import os
from pathlib import Path
from unittest.mock import MagicMock

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


def test_delete_book_rejected_while_book_has_pending_task(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    ChromaStore(persist_dir=str(tmp_path))._collection("ostep")

    fake_queue = MagicMock()
    fake_queue.book_has_pending_or_active_task.return_value = True
    monkeypatch.setattr("pipeline.api.routes_books.get_import_queue", lambda: fake_queue)

    resp = client.delete("/books/ostep")
    assert resp.status_code == 409
    fake_queue.book_has_pending_or_active_task.assert_called_once_with("ostep")


def test_delete_book_rejected_while_busy_even_if_book_never_existed(tmp_path, monkeypatch):
    # 回归测试：一本书第一次导入、还没跑到阶段3之前，collection 根本没建
    # 出来，store.list_books() 查不到它——如果"存在检查"排在"忙碌检查"
    # 前面，这里会被 404 抢跑，忙碌检查永远轮不到，导致正在导入的全新书
    # 能被绕过保护直接删除。这里不建 collection（模拟"还没到阶段3"），
    # 必须依然拿到 409，不是 404。
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    fake_queue = MagicMock()
    fake_queue.book_has_pending_or_active_task.return_value = True
    monkeypatch.setattr("pipeline.api.routes_books.get_import_queue", lambda: fake_queue)

    resp = client.delete("/books/brand-new-book")
    assert resp.status_code == 409
    fake_queue.book_has_pending_or_active_task.assert_called_once_with("brand-new-book")


def test_delete_book_allowed_for_unrelated_book(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    ChromaStore(persist_dir=str(tmp_path))._collection("ostep")

    fake_queue = MagicMock()
    fake_queue.book_has_pending_or_active_task.return_value = False
    monkeypatch.setattr("pipeline.api.routes_books.get_import_queue", lambda: fake_queue)

    resp = client.delete("/books/ostep")
    assert resp.status_code == 200


def test_delete_file_rejected_while_book_has_pending_task(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    ChromaStore(persist_dir=str(tmp_path))._collection("ostep")
    _write_manifest(tmp_path, "ostep", {"abc": "ch01.pdf"})

    fake_queue = MagicMock()
    fake_queue.book_has_pending_or_active_task.return_value = True
    monkeypatch.setattr("pipeline.api.routes_books.get_import_queue", lambda: fake_queue)

    resp = client.delete("/books/ostep/files/ch01.pdf")
    assert resp.status_code == 409


def test_delete_file_rejected_while_busy_even_if_book_never_existed(tmp_path, monkeypatch):
    # 同源回归测试（见 test_delete_book_rejected_while_busy_even_if_book_never_existed
    # 的解释）。这条目前前端摸不到（FileList 依赖 list_files，book 不存在时
    # 文件列表本身拿不到），但后端不能靠"没有调用方"当理由跳过防护。
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    fake_queue = MagicMock()
    fake_queue.book_has_pending_or_active_task.return_value = True
    monkeypatch.setattr("pipeline.api.routes_books.get_import_queue", lambda: fake_queue)

    resp = client.delete("/books/brand-new-book/files/ch01.pdf")
    assert resp.status_code == 409


def test_delete_book_removes_all_on_disk_records(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    ChromaStore(persist_dir=str(tmp_path))._collection("ostep")
    manifest_dir = tmp_path / ".manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    suffixes = ["json", "failures.json", "parse_cache.json",
                "vlm_cache.json", "pending_files.json"]
    for suffix in suffixes:
        (manifest_dir / f"ostep.{suffix}").write_text("{}")
    # 别的书的记录不能被误删
    (manifest_dir / "other.json").write_text("{}")

    resp = client.delete("/books/ostep")

    assert resp.status_code == 200
    for suffix in suffixes:
        assert not (manifest_dir / f"ostep.{suffix}").exists(), suffix
    assert (manifest_dir / "other.json").exists()


def test_delete_book_without_on_disk_records_still_succeeds(tmp_path, monkeypatch):
    """一本书可能从来没导入过任何文件——manifest 等文件不存在时删书不能报错。"""
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    ChromaStore(persist_dir=str(tmp_path))._collection("ostep")

    resp = client.delete("/books/ostep")

    assert resp.status_code == 200


def test_delete_book_removes_conversations(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    ChromaStore(persist_dir=str(tmp_path))._collection("ostep")
    client.post("/books/ostep/conversations")
    assert (tmp_path / ".conversations" / "ostep").exists()

    resp = client.delete("/books/ostep")

    assert resp.status_code == 200
    assert not (tmp_path / ".conversations" / "ostep").exists()


def test_delete_book_without_conversations_still_succeeds(tmp_path, monkeypatch):
    """从没开过对话的书删除时不能因为目录不存在而报错。"""
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    ChromaStore(persist_dir=str(tmp_path))._collection("ostep")

    resp = client.delete("/books/ostep")

    assert resp.status_code == 200


def test_rename_book_not_found(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    resp = client.patch("/books/missing", json={"new_book_id": "new"})
    assert resp.status_code == 404


def test_rename_book_conflict_when_new_id_exists(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    ChromaStore(persist_dir=str(tmp_path))._collection("book-a")
    ChromaStore(persist_dir=str(tmp_path))._collection("book-b")
    resp = client.patch("/books/book-a", json={"new_book_id": "book-b"})
    assert resp.status_code == 409


def test_rename_book_rejected_while_busy(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    ChromaStore(persist_dir=str(tmp_path))._collection("book-a")
    fake_queue = MagicMock()
    fake_queue.book_has_pending_or_active_task.return_value = True
    monkeypatch.setattr("pipeline.api.routes_books.get_import_queue", lambda: fake_queue)
    resp = client.patch("/books/book-a", json={"new_book_id": "book-b"})
    assert resp.status_code == 409


def test_rename_book_rejected_while_busy_even_if_book_never_existed(tmp_path, monkeypatch):
    # 同源回归测试（见 test_delete_book_rejected_while_busy_even_if_book_never_existed
    # 的解释）——前端目前双击改名不做任何忙碌检查，完全靠后端兜底，
    # 后端自己更不能把这个漏洞留着。
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    fake_queue = MagicMock()
    fake_queue.book_has_pending_or_active_task.return_value = True
    monkeypatch.setattr("pipeline.api.routes_books.get_import_queue", lambda: fake_queue)

    resp = client.patch("/books/brand-new-book", json={"new_book_id": "renamed"})
    assert resp.status_code == 409
    fake_queue.book_has_pending_or_active_task.assert_called_once_with("brand-new-book")


def test_rename_book_renames_everything(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    ChromaStore(persist_dir=str(tmp_path))._collection("old")
    manifest_dir = tmp_path / ".manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_suffixes = ("json", "failures.json", "parse_cache.json", "vlm_cache.json")
    for suffix in manifest_suffixes:
        (manifest_dir / f"old.{suffix}").write_text("{}")
    (manifest_dir / "old.pending_files.json").write_text('["/x/ch01.pdf"]')
    conv_id = client.post("/books/old/conversations").json()["id"]

    resp = client.patch("/books/old", json={"new_book_id": "new"})

    assert resp.status_code == 200
    assert resp.json() == {"book_id": "new"}
    assert client.get("/books").json() == {"books": ["new"]}
    for suffix in manifest_suffixes:
        assert (manifest_dir / f"new.{suffix}").exists(), suffix
        assert not (manifest_dir / f"old.{suffix}").exists(), suffix
    assert (manifest_dir / "new.pending_files.json").exists()
    assert client.get(f"/books/new/conversations/{conv_id}").status_code == 200
    assert client.get(f"/books/old/conversations/{conv_id}").status_code == 404


def test_rename_book_evicts_cached_agent_client(tmp_path, monkeypatch):
    from pipeline.api import agent_registry
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    ChromaStore(persist_dir=str(tmp_path))._collection("old")
    agent_registry.reset_registry()
    monkeypatch.setattr(agent_registry, "_clients", {"old": object()})

    resp = client.patch("/books/old", json={"new_book_id": "new"})

    assert resp.status_code == 200
    assert "old" not in agent_registry._clients
    agent_registry.reset_registry()
