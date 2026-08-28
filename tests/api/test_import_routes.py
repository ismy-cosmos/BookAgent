from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from pipeline.api.app import app

client = TestClient(app)


def _fake_queue(monkeypatch, **attrs):
    fake = MagicMock()
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
    from pipeline.api import busy_state

    fake = _fake_queue(monkeypatch)
    fake.get_progress.return_value = {
        "progress": {"stage": "vlm", "current_file": 3, "total_files": 3,
                     "current_image": 7, "total_images": 40},
        "last_result": None,
    }

    busy_state.try_acquire("ingesting", "ostep")
    try:
        resp = client.get("/progress")

        assert resp.status_code == 200
        assert resp.json() == {
            "busy": True, "reason": "ingesting", "book_id": "ostep", "pause_requested": False,
            "progress": {"stage": "vlm", "current_file": 3, "total_files": 3,
                         "current_image": 7, "total_images": 40},
            "last_result": None,
        }
    finally:
        busy_state.release()


def test_progress_reflects_answering_busy_state(tmp_path, monkeypatch):
    """issue #36：/progress 之前直接问 ImportQueue.get_status()，看不到
    "回答中"这个忙碌原因——ImportPanel/FileList/GlobalImportCapsule 走的
    都是这个接口，不修的话这三个组件会完全看不到新状态。这个场景下
    ImportQueue 本身完全空闲，不需要 _fake_queue()。"""
    from pipeline.api import busy_state
    busy_state.try_acquire("answering", "ostep")
    try:
        resp = client.get("/progress")
        assert resp.status_code == 200
        body = resp.json()
        assert body["busy"] is True
        assert body["reason"] == "answering"
        assert body["book_id"] == "ostep"
        assert body["progress"] is None
        assert body["last_result"] is None
    finally:
        busy_state.release()


# ── 暂停/恢复 ────────────────────────────────────────────────────────────

def test_pause_endpoint_requests_pause_and_returns_shared_status(tmp_path, monkeypatch):
    from pipeline.api import busy_state

    fake = _fake_queue(monkeypatch)

    busy_state.try_acquire("ingesting", "ostep")
    try:
        resp = client.post("/import/pause")

        assert resp.status_code == 200
        fake.request_pause.assert_called_once_with()
        body = resp.json()
        assert body["busy"] is True
        assert body["reason"] == "ingesting"
        assert body["book_id"] == "ostep"
        # pause_requested 来自真实的 ImportQueue 单例（status.py 里的
        # get_status() 自己 import 的 get_import_queue，跟这里 _fake_queue()
        # 打桩的 routes_import.get_import_queue 是两个不同的引用，前者不会
        # 被这个 mock 拦到）——这里只确认它是个真布尔值，不断言具体
        # True/False，避免测试跟"真实单例这次会话里没被弄脏"这种隐含假设
        # 绑死。
        assert isinstance(body["pause_requested"], bool)
    finally:
        busy_state.release()


def test_pause_endpoint_reflects_answering_busy_state(tmp_path, monkeypatch):
    """issue #36 回归：/import/pause 之前直接问 ImportQueue.get_status()，
    看不到"回答中"这个忙碌原因——跟 /progress 当时漏改是同一类 bug，只是
    这一个调用点被漏掉了。这个场景下 ImportQueue 本身完全空闲，不需要
    _fake_queue()（跟 test_progress_reflects_answering_busy_state 是同一个
    写法）。"""
    from pipeline.api import busy_state

    busy_state.try_acquire("answering", "ostep")
    try:
        resp = client.post("/import/pause")
        assert resp.status_code == 200
        body = resp.json()
        assert body["busy"] is True
        assert body["reason"] == "answering"
        assert body["book_id"] == "ostep"
    finally:
        busy_state.release()


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
