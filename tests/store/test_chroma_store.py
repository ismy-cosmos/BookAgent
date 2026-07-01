import pytest
from unittest.mock import MagicMock, patch
from pipeline.chunk.schema import Chunk
from pipeline.store import ChromaStore


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
