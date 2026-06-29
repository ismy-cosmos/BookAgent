import pytest
from unittest.mock import MagicMock, patch
from pipeline.chunk.schema import Chunk
from pipeline.store import ChromaStore


def _chunk(chunk_id="b/f/p0001/0000", page_start=1, start_sec=None, end_sec=None):
    return Chunk(
        chunk_id=chunk_id,
        book_id="b",
        source_file="f.pdf",
        element_type="text",
        content="Some content.",
        token_count=3,
        page_start=page_start,
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


def test_query_returns_formatted_results(mock_chroma):
    _, mock_col, tmp = mock_chroma
    mock_col.query.return_value = {
        "ids": [["b/f/p0001/0000"]],
        "documents": [["Some content."]],
        "distances": [[0.12]],
        "metadatas": [[{"page_start": 1, "start_sec": "", "end_sec": ""}]],
    }
    store = ChromaStore(persist_dir=str(tmp))
    results = store.query("b", [0.0] * 1024, n_results=1)
    assert len(results) == 1
    assert results[0]["chunk_id"] == "b/f/p0001/0000"
    assert results[0]["content"] == "Some content."
    assert results[0]["score"] == pytest.approx(0.12)
    assert results[0]["page_start"] == 1
    assert results[0]["start_sec"] is None


def test_count_returns_int(mock_chroma):
    _, mock_col, tmp = mock_chroma
    mock_col.count.return_value = 42
    store = ChromaStore(persist_dir=str(tmp))
    assert store.count("b") == 42
