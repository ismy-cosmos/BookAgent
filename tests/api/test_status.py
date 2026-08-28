from fastapi.testclient import TestClient

from pipeline.api.app import app
from pipeline.api import busy_state

client = TestClient(app)


def test_status_idle_by_default():
    resp = client.get("/status")
    assert resp.status_code == 200
    assert resp.json() == {
        "busy": False, "reason": "idle", "book_id": None, "pause_requested": False,
    }


def test_status_reflects_answering():
    busy_state.try_acquire("answering", "ostep")
    try:
        resp = client.get("/status")
        assert resp.json() == {
            "busy": True, "reason": "answering", "book_id": "ostep", "pause_requested": False,
        }
    finally:
        busy_state.release()


def test_status_reflects_ingesting():
    busy_state.try_acquire("ingesting", "ostep")
    try:
        resp = client.get("/status")
        assert resp.json() == {
            "busy": True, "reason": "ingesting", "book_id": "ostep", "pause_requested": False,
        }
    finally:
        busy_state.release()


def test_status_pause_requested_independent_of_busy_state_reason():
    """pause_requested 是 ImportQueue 自己的状态，即便当前忙碌状态跟导入
    完全无关（比如回答问题），它也要照实反映 ImportQueue 那边的值，不能
    被 busy_state 那边的忙碌原因覆盖或忽略。"""
    from pipeline.api.import_queue import get_import_queue
    q = get_import_queue()
    # 直接操作内部事件模拟"有一个暂停请求还没清掉"这个状态，不依赖真的
    # 起一个任务——is_pause_requested() 单测已经覆盖真实场景，这里只关心
    # get_status() 是否正确转发它。
    q._pause_event.set()
    busy_state.try_acquire("answering", "ostep")
    try:
        resp = client.get("/status")
        body = resp.json()
        assert body["pause_requested"] is True
        assert body["reason"] == "answering"
    finally:
        q._pause_event.clear()
        busy_state.release()
