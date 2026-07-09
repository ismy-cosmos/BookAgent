from fastapi.testclient import TestClient

from pipeline.api.app import app

client = TestClient(app)


def test_status_idle_by_default():
    resp = client.get("/status")
    assert resp.status_code == 200
    assert resp.json() == {
        "busy": False, "reason": "idle", "book_id": None, "pause_requested": False,
    }
