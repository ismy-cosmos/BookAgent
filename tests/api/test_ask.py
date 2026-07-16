from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from pipeline.api.app import app
from pipeline.chunk.schema import Chunk

client = TestClient(app)


def _fake_turn(final_answer="答案", triggered_tool=None, retrieved_chunks=None,
               total_tokens=42, latency_s=0.5, used_calculate=False, attempted_retrieve=False):
    turn = MagicMock()
    turn.final_answer = final_answer
    turn.triggered_tool = triggered_tool
    turn.retrieved_chunks = retrieved_chunks or []
    turn.total_tokens = total_tokens
    turn.latency_s = latency_s
    turn.used_calculate = used_calculate
    turn.attempted_retrieve = attempted_retrieve
    return turn


def _make_one_chunk() -> list[Chunk]:
    return [Chunk(
        chunk_id="c1", book_id="ostep", source_file="ch3.pdf",
        element_type="text", content="fork() 相关内容", token_count=10,
        page_start=1, page_end=1, start_sec=None, end_sec=None, low_confidence=False,
    )]


def test_ask_conversation_not_found(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    resp = client.post("/books/ostep/conversations/does-not-exist/ask", json={"question": "Q"})
    assert resp.status_code == 404


def test_ask_book_has_no_chunks_returns_400(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    conv_id = client.post("/books/ostep/conversations").json()["id"]
    # book_id 存在于 ChromaStore（get_or_create_collection 会自动建空 collection），
    # 但没有任何 chunk —— 模拟"文件全导入失败"的场景
    resp = client.post(
        f"/books/ostep/conversations/{conv_id}/ask",
        json={"question": "Q"},
    )
    assert resp.status_code == 400
    assert "没有可用内容" in resp.json()["detail"]


def test_ask_ollama_unreachable_returns_503(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    conv_id = client.post("/books/ostep/conversations").json()["id"]

    from pipeline.store.chroma_store import ChromaStore
    store = ChromaStore(persist_dir=str(tmp_path))
    store.add_chunks("ostep", _make_one_chunk(), embeddings=[[0.0] * 8])

    fake_client = MagicMock()
    fake_client.run.side_effect = ConnectionError("Ollama 没起来")
    monkeypatch.setattr(
        "pipeline.api.routes_conversations.get_client",
        lambda book_id: fake_client,
    )

    resp = client.post(
        f"/books/ostep/conversations/{conv_id}/ask",
        json={"question": "Q"},
    )
    assert resp.status_code == 503
    assert "Ollama" in resp.json()["detail"]


def test_ask_returns_answer_and_citations(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    conv_id = client.post("/books/ostep/conversations").json()["id"]

    from pipeline.store.chroma_store import ChromaStore
    store = ChromaStore(persist_dir=str(tmp_path))
    store.add_chunks("ostep", _make_one_chunk(), embeddings=[[0.0] * 8])

    fake_client = MagicMock()
    fake_client.run.return_value = _fake_turn(
        final_answer="fork 创建子进程副本",
        retrieved_chunks=[{
            "chunk_id": "c1", "source_file": "ch3.pdf",
            "element_type": "text", "citation": "第3章", "score": 0.9,
        }],
    )
    monkeypatch.setattr(
        "pipeline.api.routes_conversations.get_client",
        lambda book_id: fake_client,
    )

    resp = client.post(
        f"/books/ostep/conversations/{conv_id}/ask",
        json={"question": "fork() 是什么？"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] == "fork 创建子进程副本\n[引用来源：第3章]"
    assert body["citations"][0]["chunk_id"] == "c1"
    assert body["total_tokens"] == 42

    # 历史要被持久化下来
    record = client.get(f"/books/ostep/conversations/{conv_id}").json()
    assert len(record["turns"]) == 1
    assert record["turns"][0]["question"] == "fork() 是什么？"


def test_ask_rejected_while_another_book_is_importing(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    conv_id = client.post("/books/ostep/conversations").json()["id"]

    from pipeline.api import busy_state
    busy_state.try_acquire("ingesting", "other-book")
    try:
        resp = client.post(
            f"/books/ostep/conversations/{conv_id}/ask",
            json={"question": "Q"},
        )
        assert resp.status_code == 409
        assert "正在导入书籍" in resp.json()["detail"]
    finally:
        busy_state.release()


def test_ask_rejected_while_another_book_is_being_answered(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    conv_id = client.post("/books/ostep/conversations").json()["id"]

    from pipeline.api import busy_state
    busy_state.try_acquire("answering", "other-book")
    try:
        resp = client.post(
            f"/books/ostep/conversations/{conv_id}/ask",
            json={"question": "Q"},
        )
        assert resp.status_code == 409
        assert "其他对话正在处理中" in resp.json()["detail"]
    finally:
        busy_state.release()


def test_ask_releases_busy_state_after_success(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    conv_id = client.post("/books/ostep/conversations").json()["id"]

    from pipeline.store.chroma_store import ChromaStore
    store = ChromaStore(persist_dir=str(tmp_path))
    store.add_chunks("ostep", _make_one_chunk(), embeddings=[[0.0] * 8])

    fake_client = MagicMock()
    fake_client.run.return_value = _fake_turn(final_answer="ok")
    monkeypatch.setattr(
        "pipeline.api.routes_conversations.get_client",
        lambda book_id: fake_client,
    )

    from pipeline.api import busy_state
    resp = client.post(
        f"/books/ostep/conversations/{conv_id}/ask",
        json={"question": "Q"},
    )
    assert resp.status_code == 200
    assert busy_state.get_state() is None


def test_ask_releases_busy_state_when_answer_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    conv_id = client.post("/books/ostep/conversations").json()["id"]

    from pipeline.store.chroma_store import ChromaStore
    store = ChromaStore(persist_dir=str(tmp_path))
    store.add_chunks("ostep", _make_one_chunk(), embeddings=[[0.0] * 8])

    fake_client = MagicMock()
    fake_client.run.side_effect = ConnectionError("Ollama 没起来")
    monkeypatch.setattr(
        "pipeline.api.routes_conversations.get_client",
        lambda book_id: fake_client,
    )

    from pipeline.api import busy_state
    resp = client.post(
        f"/books/ostep/conversations/{conv_id}/ask",
        json={"question": "Q"},
    )
    assert resp.status_code == 503
    assert busy_state.get_state() is None


def test_two_concurrent_asks_second_one_rejected(tmp_path, monkeypatch):
    """两个不同书的问答请求撞在一起，后到的直接 409（issue #36 缺口2）。"""
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    conv_id = client.post("/books/other-book/conversations").json()["id"]

    from pipeline.api import busy_state
    busy_state.try_acquire("answering", "ostep")  # 模拟另一本书正在被回答
    try:
        resp = client.post(
            f"/books/other-book/conversations/{conv_id}/ask",
            json={"question": "Q"},
        )
        assert resp.status_code == 409
    finally:
        busy_state.release()


def test_ask_response_includes_used_calculate_and_attempted_retrieve(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    conv_id = client.post("/books/ostep/conversations").json()["id"]

    from pipeline.store.chroma_store import ChromaStore
    store = ChromaStore(persist_dir=str(tmp_path))
    store.add_chunks("ostep", _make_one_chunk(), embeddings=[[0.0] * 8])

    fake_client = MagicMock()
    fake_client.run.return_value = _fake_turn(
        final_answer="35 mg", used_calculate=True, attempted_retrieve=False,
    )
    monkeypatch.setattr(
        "pipeline.api.routes_conversations.get_client",
        lambda book_id: fake_client,
    )

    resp = client.post(
        f"/books/ostep/conversations/{conv_id}/ask",
        json={"question": "用药量是多少？"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["used_calculate"] is True
    assert body["attempted_retrieve"] is False

    # 持久化的历史记录也要带上这两个字段，不只是这次响应
    record = client.get(f"/books/ostep/conversations/{conv_id}").json()
    assert record["turns"][0]["used_calculate"] is True
    assert record["turns"][0]["attempted_retrieve"] is False
