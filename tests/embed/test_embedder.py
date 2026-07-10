from unittest.mock import MagicMock, patch
import pytest
from pipeline.embed import Embedder
from pipeline.embed.embedder import release_gpu_model
import pipeline.embed.embedder as emb_mod


@pytest.fixture(autouse=True)
def reset_model_cache():
    emb_mod._MODEL_CACHE = {}
    yield
    emb_mod._MODEL_CACHE = {}
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
        assert mock_cls.call_count == 1  # shared model (same default device)


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


# ── device selection ─────────────────────────────────────────────────────────

def test_embedder_default_device_does_not_pass_devices_kwarg():
    with patch("FlagEmbedding.BGEM3FlagModel") as mock_cls:
        mock_cls.return_value = _mock_model(["x"])
        Embedder().embed(["x"])
        assert "devices" not in mock_cls.call_args.kwargs


def test_embedder_explicit_device_passes_devices_kwarg():
    with patch("FlagEmbedding.BGEM3FlagModel") as mock_cls:
        mock_cls.return_value = _mock_model(["x"])
        Embedder(device="cpu").embed(["x"])
        assert mock_cls.call_args.kwargs["devices"] == "cpu"


def test_embedder_different_devices_get_separate_cache_entries():
    with patch("FlagEmbedding.BGEM3FlagModel") as mock_cls:
        mock_cls.return_value = _mock_model(["x"])
        Embedder(device="cpu").embed(["x"])
        Embedder(device="cuda:0").embed(["y"])
        assert mock_cls.call_count == 2  # each device loads its own model instance


def test_embedder_same_explicit_device_shares_cache():
    with patch("FlagEmbedding.BGEM3FlagModel") as mock_cls:
        mock_cls.return_value = _mock_model(["x"])
        Embedder(device="cpu").embed(["x"])
        Embedder(device="cpu").embed(["y"])
        assert mock_cls.call_count == 1  # same device string, shared model


# ── release_gpu_model ────────────────────────────────────────────────────────

def test_release_gpu_model_forces_reload_on_next_use():
    with patch("FlagEmbedding.BGEM3FlagModel") as mock_cls:
        mock_cls.return_value = _mock_model(["x"])
        Embedder().embed(["x"])
        assert mock_cls.call_count == 1

        release_gpu_model()
        Embedder().embed(["y"])
        assert mock_cls.call_count == 2  # cache was cleared, reloaded from scratch


def test_release_gpu_model_does_not_touch_cpu_device_cache():
    """device="cpu" 那份是查询用的，跟导入的 GPU 那份分开缓存，不该被一起清掉。"""
    with patch("FlagEmbedding.BGEM3FlagModel") as mock_cls:
        mock_cls.return_value = _mock_model(["x"])
        Embedder().embed(["gpu-one"])            # 缓存键 "auto"
        Embedder(device="cpu").embed(["cpu-one"])  # 缓存键 "cpu"
        assert mock_cls.call_count == 2

        release_gpu_model()
        Embedder(device="cpu").embed(["cpu-two"])
        assert mock_cls.call_count == 2  # cpu 缓存还在，没有重新加载


def test_release_gpu_model_is_a_no_op_when_nothing_cached():
    release_gpu_model()  # 不应抛异常