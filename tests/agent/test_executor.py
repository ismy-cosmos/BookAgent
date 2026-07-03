import json
import pytest
from decimal import Decimal


# ── safe_calculate ────────────────────────────────────────────────────────────

def test_safe_calculate_addition():
    from pipeline.agent.executor import safe_calculate
    assert safe_calculate("1 + 1") == "2"


def test_safe_calculate_decimal_precision():
    from pipeline.agent.executor import safe_calculate
    # float("0.1 + 0.2") == 0.30000000000000004；Decimal 应精确
    result = safe_calculate("0.1 + 0.2")
    assert Decimal(result) == Decimal("0.3")


def test_safe_calculate_multiplication():
    from pipeline.agent.executor import safe_calculate
    assert safe_calculate("0.5 * 70") == "35"


def test_safe_calculate_power():
    from pipeline.agent.executor import safe_calculate
    assert safe_calculate("2 ** 10") == "1024"


def test_safe_calculate_floor_division():
    from pipeline.agent.executor import safe_calculate
    assert safe_calculate("512 // 16") == "32"


def test_safe_calculate_parentheses():
    from pipeline.agent.executor import safe_calculate
    result = Decimal(safe_calculate("(100 - 37) / 2"))
    assert result == Decimal("31.5")


def test_safe_calculate_rejects_import():
    from pipeline.agent.executor import safe_calculate
    with pytest.raises(ValueError, match="不允许"):
        safe_calculate("__import__('os').system('ls')")


def test_safe_calculate_rejects_function_call():
    from pipeline.agent.executor import safe_calculate
    with pytest.raises(ValueError, match="不允许"):
        safe_calculate("open('file').read()")


def test_safe_calculate_rejects_division_by_zero():
    from pipeline.agent.executor import safe_calculate
    with pytest.raises(ValueError, match="零"):
        safe_calculate("1 / 0")


def test_safe_calculate_rejects_invalid_syntax():
    from pipeline.agent.executor import safe_calculate
    with pytest.raises(ValueError):
        safe_calculate("not valid math !!!")


def test_safe_calculate_no_scientific_notation():
    from pipeline.agent.executor import safe_calculate
    # Regression test: safe_calculate should avoid E-notation for trailing-zero integers
    assert safe_calculate("125 * 8") == "1000"
    assert safe_calculate("120000 * 0.15") == "18000"
    # Verify existing precision test still passes
    result = safe_calculate("0.1 + 0.2")
    assert Decimal(result) == Decimal("0.3")


# ── ChunkResult ───────────────────────────────────────────────────────────────

def test_chunk_result_has_all_required_fields():
    from pipeline.agent.executor import ChunkResult
    chunk = ChunkResult(
        chunk_id="c001",
        book_title="深度学习",
        page_num=42,
        chapter="第三章",
        content="注意力机制的核心公式为 Attention(Q,K,V)=softmax(QK^T/√d_k)V",
        preview="注意力机制的核心公式",
        keyword_highlights=["注意力", "softmax"],
        relevance_score=0.92,
        source_path="/data/books/dl.pdf",
    )
    assert chunk.chunk_id == "c001"
    assert chunk.page_num == 42
    assert chunk.relevance_score == 0.92
    assert isinstance(chunk.keyword_highlights, list)


def test_chunk_result_serializable_to_json():
    from pipeline.agent.executor import ChunkResult
    import dataclasses
    chunk = ChunkResult(
        chunk_id="c001", book_title="测试书", page_num=1, chapter="第一章",
        content="内容", preview="内容", keyword_highlights=["关键词"],
        relevance_score=0.8, source_path="/path/book.pdf",
    )
    d = dataclasses.asdict(chunk)
    json.dumps(d)  # must not raise


# ── StubExecutor ──────────────────────────────────────────────────────────────

def test_stub_executor_retrieve_returns_json_list():
    from pipeline.agent.executor import StubExecutor
    stub = StubExecutor()
    result = stub.execute("retrieve", {"query": "注意力机制", "k": 3})
    data = json.loads(result)
    assert isinstance(data, list)
    assert len(data) <= 3


def test_stub_executor_retrieve_respects_max_results():
    from pipeline.agent.executor import StubExecutor
    stub = StubExecutor(max_results=2)
    result = stub.execute("retrieve", {"query": "任意内容", "k": 10})
    data = json.loads(result)
    assert len(data) <= 2


def test_stub_executor_retrieve_chunk_has_all_fields():
    from pipeline.agent.executor import StubExecutor
    stub = StubExecutor()
    result = stub.execute("retrieve", {"query": "测试", "k": 1})
    chunks = json.loads(result)
    assert len(chunks) >= 1
    required = {"chunk_id", "book_title", "page_num", "chapter",
                "content", "preview", "keyword_highlights",
                "relevance_score", "source_path"}
    assert required.issubset(set(chunks[0].keys()))


def test_stub_executor_retrieve_preview_is_truncated():
    from pipeline.agent.executor import StubExecutor
    stub = StubExecutor(preview_length=50)
    result = stub.execute("retrieve", {"query": "测试", "k": 1})
    chunks = json.loads(result)
    assert len(chunks[0]["preview"]) <= 50


def test_stub_executor_calculate_basic():
    from pipeline.agent.executor import StubExecutor
    stub = StubExecutor()
    result = stub.execute("calculate", {"expression": "3 * 5"})
    assert result == "15"


def test_stub_executor_calculate_invalid_raises_graceful_error():
    from pipeline.agent.executor import StubExecutor
    stub = StubExecutor()
    result = stub.execute("calculate", {"expression": "open('x')"})
    assert "错误" in result or "Error" in result.lower()


def test_stub_executor_get_chunk_hit():
    from pipeline.agent.executor import StubExecutor
    stub = StubExecutor()
    result = stub.execute("get_chunk", {"chunk_id": "stub-001"})
    data = json.loads(result)
    assert data["chunk_id"] == "stub-001"
    assert "content" in data


def test_stub_executor_get_chunk_miss():
    from pipeline.agent.executor import StubExecutor
    stub = StubExecutor()
    result = stub.execute("get_chunk", {"chunk_id": "does-not-exist"})
    data = json.loads(result)
    assert "error" in data


def test_stub_executor_unknown_tool_raises():
    from pipeline.agent.executor import StubExecutor
    stub = StubExecutor()
    with pytest.raises(ValueError, match="未知工具"):
        stub.execute("nonexistent_tool", {})


# ── RealExecutor ──────────────────────────────────────────────────────────────

class _FakeEmbedder:
    def embed_query(self, text: str) -> list:
        return [0.1] * 1024


def _seed_chunk(store, book_id="test-book", chunk_id="b/f/p0001/0000", element_type="text",
                 page_start=1, page_end=1, start_sec=None, end_sec=None,
                 content="Some real content.", low_confidence=False):
    from pipeline.chunk.schema import Chunk
    chunk = Chunk(
        chunk_id=chunk_id, book_id=book_id, source_file="f.pdf",
        element_type=element_type, content=content, token_count=3,
        page_start=page_start, page_end=page_end,
        start_sec=start_sec, end_sec=end_sec, low_confidence=low_confidence,
    )
    store.add_chunks(book_id, [chunk], [[0.1] * 1024])


@pytest.fixture
def real_store(tmp_path):
    from pipeline.store import ChromaStore
    return ChromaStore(persist_dir=str(tmp_path))


def test_real_executor_retrieve_returns_honest_shape(real_store):
    from pipeline.agent.executor import RealExecutor
    _seed_chunk(real_store)
    ex = RealExecutor(book_id="test-book", embedder=_FakeEmbedder(), store=real_store)
    result = ex.execute("retrieve", {"query": "test", "k": 5})
    data = json.loads(result)
    assert len(data) == 1
    record = data[0]
    assert record["chunk_id"] == "b/f/p0001/0000"
    assert record["content"] == "Some real content."
    assert record["element_type"] == "text"
    assert record["source_file"] == "f.pdf"
    assert record["citation"] == "f.pdf p.1"
    assert record["low_confidence"] is False
    assert set(record.keys()) == {
        "chunk_id", "content", "element_type", "source_file",
        "citation", "low_confidence", "score",
    }


def test_real_executor_retrieve_citation_page_range(real_store):
    from pipeline.agent.executor import RealExecutor
    _seed_chunk(real_store, chunk_id="b/f/p0001/0001", page_start=5, page_end=6)
    ex = RealExecutor(book_id="test-book", embedder=_FakeEmbedder(), store=real_store)
    data = json.loads(ex.execute("retrieve", {"query": "q"}))
    assert data[0]["citation"] == "f.pdf p.5-6"


def test_real_executor_retrieve_citation_audio_mmss(real_store):
    from pipeline.agent.executor import RealExecutor
    _seed_chunk(real_store, chunk_id="b/a/0000", element_type="audio",
                page_start=None, page_end=None, start_sec=75.0, end_sec=101.0)
    ex = RealExecutor(book_id="test-book", embedder=_FakeEmbedder(), store=real_store)
    data = json.loads(ex.execute("retrieve", {"query": "q"}))
    assert data[0]["citation"] == "f.pdf 01:15-01:41"


def test_real_executor_retrieve_citation_no_location(real_store):
    from pipeline.agent.executor import RealExecutor
    _seed_chunk(real_store, chunk_id="b/img/0000", element_type="figure",
                page_start=None, page_end=None)
    ex = RealExecutor(book_id="test-book", embedder=_FakeEmbedder(), store=real_store)
    data = json.loads(ex.execute("retrieve", {"query": "q"}))
    assert data[0]["citation"] == "f.pdf"


def test_real_executor_retrieve_respects_k_cap(real_store):
    from pipeline.agent.executor import RealExecutor
    for i in range(3):
        _seed_chunk(real_store, chunk_id=f"b/f/p0001/000{i}")
    ex = RealExecutor(book_id="test-book", embedder=_FakeEmbedder(), store=real_store, max_results=10)
    data = json.loads(ex.execute("retrieve", {"query": "q", "k": 99}))
    assert len(data) <= 10


def test_real_executor_retrieve_empty_book_returns_empty_list(real_store):
    from pipeline.agent.executor import RealExecutor
    ex = RealExecutor(book_id="empty-book", embedder=_FakeEmbedder(), store=real_store)
    data = json.loads(ex.execute("retrieve", {"query": "q"}))
    assert data == []


def test_real_executor_get_chunk_hit(real_store):
    from pipeline.agent.executor import RealExecutor
    _seed_chunk(real_store, chunk_id="b/f/p0001/0000")
    ex = RealExecutor(book_id="test-book", embedder=_FakeEmbedder(), store=real_store)
    data = json.loads(ex.execute("get_chunk", {"chunk_id": "b/f/p0001/0000"}))
    assert data["chunk_id"] == "b/f/p0001/0000"
    assert data["content"] == "Some real content."


def test_real_executor_get_chunk_miss(real_store):
    from pipeline.agent.executor import RealExecutor
    ex = RealExecutor(book_id="test-book", embedder=_FakeEmbedder(), store=real_store)
    data = json.loads(ex.execute("get_chunk", {"chunk_id": "nonexistent"}))
    assert "error" in data


def test_real_executor_calculate_delegates_to_safe_calculate(real_store):
    from pipeline.agent.executor import RealExecutor
    ex = RealExecutor(book_id="test-book", embedder=_FakeEmbedder(), store=real_store)
    assert ex.execute("calculate", {"expression": "3 * 5"}) == "15"


def test_real_executor_calculate_invalid_returns_graceful_error(real_store):
    from pipeline.agent.executor import RealExecutor
    ex = RealExecutor(book_id="test-book", embedder=_FakeEmbedder(), store=real_store)
    result = ex.execute("calculate", {"expression": "1/0"})
    assert "错误" in result


def test_real_executor_unknown_tool_raises(real_store):
    from pipeline.agent.executor import RealExecutor
    ex = RealExecutor(book_id="test-book", embedder=_FakeEmbedder(), store=real_store)
    with pytest.raises(ValueError, match="未知工具"):
        ex.execute("nonexistent", {})
