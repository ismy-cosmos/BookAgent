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


def test_get_chunk_with_real_slash_containing_id(tmp_path, monkeypatch):
    # 真实 chunk_id 格式是 "{book_id}/{文件名}/{页码}/{序号}"（见
    # chunker.py::_make_chunk_id），字符串里带斜杠——前端 encodeURIComponent
    # 会把斜杠编码成 %2F，但 uvicorn 在路由匹配前会先解码回真的 "/"，
    # 如果路由参数不是 :path 类型就会匹配失败，返回 FastAPI 自带的
    # 通用 404（不是我们自己写的"未找到 chunk"提示），前端表现为
    # 点引用胶囊永远显示"Not Found"。之前唯一的测试用的是不含斜杠的
    # "c1"，没测出这个真实存在的路由 bug。
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path))
    store = ChromaStore(persist_dir=str(tmp_path))
    chunk = Chunk(
        chunk_id="ostep/ch3.pdf/p0001/0000", book_id="ostep", source_file="ch3.pdf",
        element_type="text", content="fork() 相关内容", token_count=10,
        page_start=42, page_end=42, start_sec=None, end_sec=None, low_confidence=False,
    )
    store.add_chunks("ostep", [chunk], embeddings=[[0.0] * 8])

    resp = client.get("/books/ostep/chunks/ostep%2Fch3.pdf%2Fp0001%2F0000")

    assert resp.status_code == 200
    body = resp.json()
    assert body["chunk_id"] == "ostep/ch3.pdf/p0001/0000"
    assert body["content"] == "fork() 相关内容"
