from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from pipeline.api.app import app

client = TestClient(app)


def _fake_queue(monkeypatch, **attrs):
    fake = MagicMock()
    fake.get_status.return_value = {
        "busy": False, "reason": "idle", "book_id": None, "pause_requested": False,
    }
    fake.get_progress.return_value = {"progress": None, "last_result": None}
    for k, v in attrs.items():
        setattr(fake, k, v)
    monkeypatch.setattr("pipeline.api.routes_import.get_import_queue", lambda: fake)
    return fake


# ── 待导入列表 CRUD ──────────────────────────────────────────────────────

def test_staged_files_empty_for_new_book(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    resp = client.get("/books/newbook/staged-files")
    assert resp.status_code == 200
    assert resp.json() == {"files": []}


def test_add_staged_file_success(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    f = tmp_path / "ch01.pdf"
    f.write_bytes(b"content")

    resp = client.post("/books/ostep/staged-files", json={"file_path": str(f)})

    assert resp.status_code == 200
    assert resp.json() == {"files": [str(f)]}
    assert client.get("/books/ostep/staged-files").json() == {"files": [str(f)]}


def test_add_staged_file_missing_path_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    resp = client.post("/books/ostep/staged-files",
                       json={"file_path": str(tmp_path / "nope.pdf")})
    assert resp.status_code == 400
    assert client.get("/books/ostep/staged-files").json() == {"files": []}


def test_add_staged_file_unsupported_extension_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    f = tmp_path / "notes.txt"
    f.write_bytes(b"text")
    resp = client.post("/books/ostep/staged-files", json={"file_path": str(f)})
    assert resp.status_code == 400


def test_add_staged_file_directory_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    d = tmp_path / "somedir.pdf"  # 扩展名合法但它是个目录
    d.mkdir()
    resp = client.post("/books/ostep/staged-files", json={"file_path": str(d)})
    assert resp.status_code == 400


def test_remove_staged_file_success(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    f = tmp_path / "ch01.pdf"
    f.write_bytes(b"content")
    client.post("/books/ostep/staged-files", json={"file_path": str(f)})

    resp = client.delete("/books/ostep/staged-files", params={"file_path": str(f)})

    assert resp.status_code == 200
    assert resp.json() == {"files": []}


def test_remove_staged_file_not_in_list_404(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    resp = client.delete("/books/ostep/staged-files",
                         params={"file_path": "/data/nope.pdf"})
    assert resp.status_code == 404


# ── 提交导入 ─────────────────────────────────────────────────────────────

def test_submit_import_enqueues_staged_files(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    f1 = tmp_path / "ch01.pdf"; f1.write_bytes(b"one")
    f2 = tmp_path / "ch02.pdf"; f2.write_bytes(b"two")
    client.post("/books/ostep/staged-files", json={"file_path": str(f1)})
    client.post("/books/ostep/staged-files", json={"file_path": str(f2)})

    fake = _fake_queue(monkeypatch)
    fake.enqueue.return_value = "task-123"

    resp = client.post("/books", json={"book_id": "ostep"})

    assert resp.status_code == 202
    assert resp.json() == {"task_id": "task-123", "file_count": 2}
    fake.enqueue.assert_called_once_with("ostep", [str(f1), str(f2)])


def test_submit_import_empty_staging_list_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    fake = _fake_queue(monkeypatch)

    resp = client.post("/books", json={"book_id": "ostep"})

    assert resp.status_code == 400
    fake.enqueue.assert_not_called()


# ── 进度轮询 ─────────────────────────────────────────────────────────────

def test_progress_merges_status_and_progress(tmp_path, monkeypatch):
    fake = _fake_queue(monkeypatch)
    fake.get_status.return_value = {
        "busy": True, "reason": "ingesting", "book_id": "ostep", "pause_requested": False,
    }
    fake.get_progress.return_value = {
        "progress": {"stage": "vlm", "current_file": 3, "total_files": 3,
                     "current_image": 7, "total_images": 40},
        "last_result": None,
    }

    resp = client.get("/progress")

    assert resp.status_code == 200
    assert resp.json() == {
        "busy": True, "reason": "ingesting", "book_id": "ostep", "pause_requested": False,
        "progress": {"stage": "vlm", "current_file": 3, "total_files": 3,
                     "current_image": 7, "total_images": 40},
        "last_result": None,
    }


# ── 暂停/恢复 ────────────────────────────────────────────────────────────

def test_pause_endpoint_requests_pause_and_returns_status(tmp_path, monkeypatch):
    fake = _fake_queue(monkeypatch)
    fake.get_status.return_value = {
        "busy": True, "reason": "ingesting", "book_id": "ostep", "pause_requested": True,
    }

    resp = client.post("/import/pause")

    assert resp.status_code == 200
    fake.request_pause.assert_called_once_with()
    assert resp.json()["pause_requested"] is True


def test_resume_endpoint_resumes_and_returns_status(tmp_path, monkeypatch):
    fake = _fake_queue(monkeypatch)

    resp = client.post("/import/resume")

    assert resp.status_code == 200
    fake.resume.assert_called_once_with()
    assert resp.json()["pause_requested"] is False


# ── 取消排队任务 ─────────────────────────────────────────────────────────

def test_cancel_queued_task_success(tmp_path, monkeypatch):
    fake = _fake_queue(monkeypatch)
    fake.cancel.return_value = True

    resp = client.post("/import/task-123/cancel")

    assert resp.status_code == 200
    assert resp.json() == {"cancelled": "task-123"}
    fake.cancel.assert_called_once_with("task-123")


def test_cancel_not_queued_task_409(tmp_path, monkeypatch):
    fake = _fake_queue(monkeypatch)
    fake.cancel.return_value = False  # 已开始处理、已完成或不存在——队列层不区分

    resp = client.post("/import/task-123/cancel")

    assert resp.status_code == 409
