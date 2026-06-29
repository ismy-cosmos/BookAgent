from unittest.mock import MagicMock, patch
import pytest
from pipeline.embed import Embedder
import pipeline.embed.embedder as emb_mod


@pytest.fixture(autouse=True)
def reset_model_cache():
    emb_mod._MODEL_CACHE = None
    yield
    emb_mod._MODEL_CACHE = None
    # also release the lock in case a test failed while holding it
    try:
        emb_mod._MODEL_LOCK.release()
    except RuntimeError:
        pass


def _mock_model(texts):
    import numpy as np
    n = len(texts)
    mock = MagicMock()
    mock.encode.return_value = {"dense_vecs": np.ones((n, 1024), dtype="float32")}
    return mock


def test_embed_returns_correct_shape():
    with patch("FlagEmbedding.BGEM3FlagModel", return_value=_mock_model(["a", "b"])):
        emb = Embedder()
        result = emb.embed(["hello", "world"])
    assert len(result) == 2
    assert len(result[0]) == 1024


def test_embed_query_returns_single_vector():
    with patch("FlagEmbedding.BGEM3FlagModel", return_value=_mock_model(["q"])):
        emb = Embedder()
        vec = emb.embed_query("what is a process?")
    assert len(vec) == 1024
    assert isinstance(vec[0], float)


def test_embedder_lazy_loads_model():
    with patch("FlagEmbedding.BGEM3FlagModel") as mock_cls:
        mock_cls.return_value = _mock_model(["x"])
        emb = Embedder()
        assert mock_cls.call_count == 0  # not loaded yet
        emb.embed(["x"])
        assert mock_cls.call_count == 1  # loaded on first use
        emb.embed(["y"])
        assert mock_cls.call_count == 1  # not loaded again


def test_embedder_class_level_cache():
    with patch("FlagEmbedding.BGEM3FlagModel") as mock_cls:
        mock_cls.return_value = _mock_model(["x"])
        e1 = Embedder()
        e2 = Embedder()
        e1.embed(["x"])
        e2.embed(["y"])
        assert mock_cls.call_count == 1  # shared model


def test_embed_query_vector_dimension():
    with patch("FlagEmbedding.BGEM3FlagModel", return_value=_mock_model(["q"])):
        emb = Embedder()
        vec = emb.embed_query("what is a process?")
    assert len(vec) == 1024


def test_embedder_model_load_failure():
    with patch("FlagEmbedding.BGEM3FlagModel", side_effect=ImportError("no FlagEmbedding")):
        emb = Embedder()
        with pytest.raises(ImportError, match="no FlagEmbedding"):
            emb.embed(["x"])
