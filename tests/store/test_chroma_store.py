import pytest
from unittest.mock import MagicMock, patch
from pipeline.chunk.schema import Chunk
from pipeline.store import ChromaStore
from pipeline.store.chroma_store import get_store, reset_store_cache


def _chunk(chunk_id="b/f/p0001/0000", page_start=1, page_end=1, start_sec=None, end_sec=None):
    return Chunk(
        chunk_id=chunk_id,
        book_id="b",
        source_file="f.pdf",
        element_type="text",
        content="Some content.",
        token_count=3,
        page_start=page_start,
        page_end=page_end,
        start_sec=start_sec,
        end_sec=end_sec,
    )


@pytest.fixture
def mock_chroma(tmp_path):
    with patch("pipeline.store.chroma_store.chromadb.PersistentClient") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        yield mock_client, mock_collection, tmp_path


def test_add_chunks_calls_collection_add(mock_chroma):
    _, mock_col, tmp = mock_chroma
    store = ChromaStore(persist_dir=str(tmp))
    chunks = [_chunk()]
    embeddings = [[0.1] * 1024]
    store.add_chunks("b", chunks, embeddings)
    mock_col.add.assert_called_once()
    call_kwargs = mock_col.add.call_args.kwargs
    assert call_kwargs["ids"] == ["b/f/p0001/0000"]
    assert len(call_kwargs["embeddings"]) == 1
    assert call_kwargs["documents"] == ["Some content."]


def test_add_chunks_metadata_none_to_empty_str(mock_chroma):
    _, mock_col, tmp = mock_chroma
    store = ChromaStore(persist_dir=str(tmp))
    chunks = [_chunk(start_sec=None, end_sec=None)]
    store.add_chunks("b", chunks, [[0.0] * 1024])
    meta = mock_col.add.call_args.kwargs["metadatas"][0]
    assert meta["start_sec"] == ""
    assert meta["end_sec"] == ""
    assert meta["page_start"] == 1
    assert meta["page_end"] == 1


def test_add_chunks_metadata_page_end_differs_from_start(mock_chroma):
    _, mock_col, tmp = mock_chroma
    store = ChromaStore(persist_dir=str(tmp))
    chunks = [_chunk(page_start=5, page_end=6)]
    store.add_chunks("b", chunks, [[0.0] * 1024])
    meta = mock_col.add.call_args.kwargs["metadatas"][0]
    assert meta["page_start"] == 5
    assert meta["page_end"] == 6


def test_add_chunks_metadata_low_confidence_passed_through(mock_chroma):
    _, mock_col, tmp = mock_chroma
    store = ChromaStore(persist_dir=str(tmp))
    chunk = Chunk(
        chunk_id="b/audio/0000",
        book_id="b",
        source_file="lecture.mp3",
        element_type="audio",
        content="mumbled text",
        token_count=2,
        start_sec=0.0,
        end_sec=5.0,
        low_confidence=True,
    )
    store.add_chunks("b", [chunk], [[0.0] * 1024])
    meta = mock_col.add.call_args.kwargs["metadatas"][0]
    assert meta["low_confidence"] is True


def test_query_returns_low_confidence(mock_chroma):
    _, mock_col, tmp = mock_chroma
    mock_col.query.return_value = {
        "ids": [["b/audio/0000"]],
        "documents": [["mumbled text"]],
        "distances": [[0.2]],
        "metadatas": [[{"start_sec": 0.0, "end_sec": 5.0, "low_confidence": True}]],
    }
    store = ChromaStore(persist_dir=str(tmp))
    results = store.query("b", [0.0] * 1024, n_results=1)
    assert results[0]["low_confidence"] is True


def test_query_returns_formatted_results(mock_chroma):
    _, mock_col, tmp = mock_chroma
    mock_col.query.return_value = {
        "ids": [["b/f/p0001/0000"]],
        "documents": [["Some content."]],
        "distances": [[0.12]],
        "metadatas": [[{"page_start": 1, "page_end": 2, "start_sec": "", "end_sec": ""}]],
    }
    store = ChromaStore(persist_dir=str(tmp))
    results = store.query("b", [0.0] * 1024, n_results=1)
    assert len(results) == 1
    assert results[0]["chunk_id"] == "b/f/p0001/0000"
    assert results[0]["content"] == "Some content."
    assert results[0]["score"] == pytest.approx(0.12)
    assert results[0]["page_start"] == 1
    assert results[0]["page_end"] == 2
    assert results[0]["start_sec"] is None


def test_count_returns_int(mock_chroma):
    _, mock_col, tmp = mock_chroma
    mock_col.count.return_value = 42
    store = ChromaStore(persist_dir=str(tmp))
    assert store.count("b") == 42


def test_query_returns_source_file_and_element_type(mock_chroma):
    _, mock_col, tmp = mock_chroma
    mock_col.query.return_value = {
        "ids": [["b/f/p0001/0000"]],
        "documents": [["Some content."]],
        "distances": [[0.12]],
        "metadatas": [[{
            "source_file": "f.pdf", "element_type": "table",
            "page_start": 1, "page_end": 1, "start_sec": "", "end_sec": "",
        }]],
    }
    store = ChromaStore(persist_dir=str(tmp))
    results = store.query("b", [0.0] * 1024, n_results=1)
    assert results[0]["source_file"] == "f.pdf"
    assert results[0]["element_type"] == "table"


def test_get_returns_matching_chunks(mock_chroma):
    _, mock_col, tmp = mock_chroma
    mock_col.get.return_value = {
        "ids": ["b/f/p0001/0000"],
        "documents": ["Some content."],
        "metadatas": [{"source_file": "f.pdf", "element_type": "text",
                        "page_start": 1, "page_end": 1, "start_sec": "", "end_sec": ""}],
    }
    store = ChromaStore(persist_dir=str(tmp))
    results = store.get("b", ["b/f/p0001/0000"])
    assert len(results) == 1
    assert results[0]["chunk_id"] == "b/f/p0001/0000"
    assert results[0]["content"] == "Some content."
    assert results[0]["source_file"] == "f.pdf"
    assert results[0]["element_type"] == "text"
    mock_col.get.assert_called_once_with(ids=["b/f/p0001/0000"], include=["documents", "metadatas"])


def test_get_missing_id_returns_fewer_results(mock_chroma):
    _, mock_col, tmp = mock_chroma
    # chroma 对不存在的 id 静默跳过，不抛异常、不产生占位记录（已用真实 chromadb 1.5.9 验证）
    mock_col.get.return_value = {
        "ids": ["b/f/p0001/0000"],
        "documents": ["Some content."],
        "metadatas": [{"source_file": "f.pdf", "element_type": "text",
                        "page_start": 1, "page_end": 1, "start_sec": "", "end_sec": ""}],
    }
    store = ChromaStore(persist_dir=str(tmp))
    results = store.get("b", ["b/f/p0001/0000", "missing-id"])
    assert len(results) == 1


def test_get_empty_ids_returns_empty_list(mock_chroma):
    _, mock_col, tmp = mock_chroma
    mock_col.get.return_value = {"ids": [], "documents": [], "metadatas": []}
    store = ChromaStore(persist_dir=str(tmp))
    assert store.get("b", []) == []


def test_query_empty_collection_returns_empty_list(mock_chroma):
    _, mock_col, tmp = mock_chroma
    mock_col.query.return_value = {
        "ids": [[]],
        "documents": [[]],
        "distances": [[]],
        "metadatas": [[]],
    }
    store = ChromaStore(persist_dir=str(tmp))
    results = store.query("b", [0.0] * 1024, n_results=5)
    assert results == []


def test_add_chunks_metadata_zero_page_start_preserved(mock_chroma):
    _, mock_col, tmp = mock_chroma
    store = ChromaStore(persist_dir=str(tmp))
    c = Chunk(
        chunk_id="b/f/pNone/0000",
        book_id="b",
        source_file="f.pdf",
        element_type="text",
        content="content",
        token_count=1,
        page_start=0,  # falsy but not None — must not become ""
    )
    store.add_chunks("b", [c], [[0.0] * 1024])
    meta = mock_col.add.call_args.kwargs["metadatas"][0]
    assert meta["page_start"] == 0


def test_add_chunks_duplicate_id_does_not_raise(mock_chroma):
    _, mock_col, tmp = mock_chroma
    store = ChromaStore(persist_dir=str(tmp))
    chunk = _chunk(chunk_id="b/f/p0001/0000")
    embeddings = [[0.1] * 1024]
    store.add_chunks("b", [chunk], embeddings)
    store.add_chunks("b", [chunk], embeddings)  # 同一 id 再次添加
    assert mock_col.add.call_count == 2  # 两次都调了 add，Chroma 自行覆盖


def test_delete_by_source_removes_only_matching_file(tmp_path):
    store = ChromaStore(persist_dir=str(tmp_path))
    keep = Chunk(
        chunk_id="book1/keep.pdf/p0001/0000", book_id="book1", source_file="keep.pdf",
        element_type="text", content="keep this", token_count=2,
    )
    remove = Chunk(
        chunk_id="book1/remove.pdf/p0001/0000", book_id="book1", source_file="remove.pdf",
        element_type="text", content="remove this", token_count=2,
    )
    store.add_chunks("book1", [keep, remove], [[0.1] * 1024, [0.2] * 1024])
    assert store.count("book1") == 2

    store.delete_by_source("book1", "remove.pdf")

    assert store.count("book1") == 1
    remaining = store.get("book1", ["book1/keep.pdf/p0001/0000", "book1/remove.pdf/p0001/0000"])
    assert [r["chunk_id"] for r in remaining] == ["book1/keep.pdf/p0001/0000"]


def test_delete_by_source_no_matching_file_is_noop(tmp_path):
    store = ChromaStore(persist_dir=str(tmp_path))
    chunk = Chunk(
        chunk_id="book1/keep.pdf/p0001/0000", book_id="book1", source_file="keep.pdf",
        element_type="text", content="keep this", token_count=2,
    )
    store.add_chunks("book1", [chunk], [[0.1] * 1024])

    store.delete_by_source("book1", "does-not-exist.pdf")

    assert store.count("book1") == 1


def test_list_books_empty(tmp_path):
    store = ChromaStore(persist_dir=str(tmp_path))
    assert store.list_books() == []


def test_list_books_after_create(tmp_path):
    store = ChromaStore(persist_dir=str(tmp_path))
    store._collection("ostep")
    store._collection("civil-law")
    assert sorted(store.list_books()) == ["civil-law", "ostep"]


def test_delete_collection_removes_book(tmp_path):
    store = ChromaStore(persist_dir=str(tmp_path))
    store._collection("ostep")
    assert "ostep" in store.list_books()
    store.delete_collection("ostep")
    assert "ostep" not in store.list_books()


def test_get_store_same_path_returns_same_instance(tmp_path):
    reset_store_cache()
    a = get_store(str(tmp_path))
    b = get_store(str(tmp_path))
    assert a is b


def test_get_store_different_paths_return_different_instances(tmp_path):
    reset_store_cache()
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    dir_a.mkdir()
    dir_b.mkdir()
    a = get_store(str(dir_a))
    b = get_store(str(dir_b))
    assert a is not b


def test_get_store_concurrent_first_access_constructs_only_once(tmp_path):
    """并发第一次访问同一路径时，底层 PersistentClient 只能被构造一次；
    多构造一次就会撞上 chromadb 的 SharedSystemClient 注册表并发损坏问题。"""
    import threading

    reset_store_cache()
    barrier = threading.Barrier(20)

    def worker():
        barrier.wait()  # 让所有线程尽量同时冲进 get_store
        return get_store(str(tmp_path))

    with patch("pipeline.store.chroma_store.chromadb.PersistentClient") as mock_cls:
        mock_cls.return_value = MagicMock()
        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    mock_cls.assert_called_once()
