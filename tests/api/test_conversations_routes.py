from fastapi.testclient import TestClient

from pipeline.api.app import app

client = TestClient(app)


def test_create_and_list_conversation(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    resp = client.post("/books/ostep/conversations")
    assert resp.status_code == 200
    conv_id = resp.json()["id"]

    listed = client.get("/books/ostep/conversations").json()["conversations"]
    assert [c["id"] for c in listed] == [conv_id]


def test_get_conversation_not_found(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    resp = client.get("/books/ostep/conversations/does-not-exist")
    assert resp.status_code == 404


def test_get_conversation_returns_full_record(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    conv_id = client.post("/books/ostep/conversations").json()["id"]
    resp = client.get(f"/books/ostep/conversations/{conv_id}")
    assert resp.status_code == 200
    assert resp.json()["turns"] == []


def test_delete_conversation(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    conv_id = client.post("/books/ostep/conversations").json()["id"]
    resp = client.delete(f"/books/ostep/conversations/{conv_id}")
    assert resp.status_code == 200
    assert client.get("/books/ostep/conversations").json()["conversations"] == []


def test_delete_conversation_not_found(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    resp = client.delete("/books/ostep/conversations/does-not-exist")
    assert resp.status_code == 404
