from unittest.mock import MagicMock, patch

import pytest

from pipeline.ollama_utils import (
    ensure_model_loaded,
    ollama_openai_base_url,
    release_model,
)


def _mock_http_client():
    client_cls = MagicMock()
    client = MagicMock()
    client_cls.return_value.__enter__.return_value = client
    return client_cls, client


def test_ensure_model_loaded_only_probes_when_model_is_loaded():
    client_cls, client = _mock_http_client()
    client.get.return_value.json.return_value = {
        "models": [{"name": "qwen3:q4km", "model": "qwen3:q4km"}],
    }

    with patch("pipeline.ollama_utils.httpx.Client", client_cls):
        ensure_model_loaded("http://localhost:11434/", "qwen3:q4km")

    client.get.assert_called_once_with(
        "http://localhost:11434/api/ps",
        timeout=10.0,
    )
    client.get.return_value.raise_for_status.assert_called_once_with()
    client.post.assert_not_called()


def test_ensure_model_loaded_posts_empty_generation_when_absent():
    client_cls, client = _mock_http_client()
    client.get.return_value.json.return_value = {
        "models": [{"name": "another-model:latest"}],
    }

    with patch("pipeline.ollama_utils.httpx.Client", client_cls):
        ensure_model_loaded("http://localhost:11434", "qwen3:q4km")

    client.post.assert_called_once_with(
        "http://localhost:11434/api/generate",
        json={"model": "qwen3:q4km", "stream": False},
        timeout=120.0,
    )
    client.post.return_value.raise_for_status.assert_called_once_with()


def test_ensure_model_loaded_propagates_probe_failure_without_loading():
    client_cls, client = _mock_http_client()
    client.get.return_value.raise_for_status.side_effect = RuntimeError("probe failed")

    with patch("pipeline.ollama_utils.httpx.Client", client_cls):
        with pytest.raises(RuntimeError, match="probe failed"):
            ensure_model_loaded("http://localhost:11434", "qwen3:q4km")

    client.post.assert_not_called()


def test_ensure_model_loaded_rejects_invalid_probe_response():
    client_cls, client = _mock_http_client()
    client.get.return_value.json.return_value = {"unexpected": []}

    with patch("pipeline.ollama_utils.httpx.Client", client_cls):
        with pytest.raises(ValueError, match="models"):
            ensure_model_loaded("http://localhost:11434", "qwen3:q4km")

    client.post.assert_not_called()


def test_ensure_model_loaded_propagates_load_failure():
    client_cls, client = _mock_http_client()
    client.get.return_value.json.return_value = {"models": []}
    client.post.return_value.raise_for_status.side_effect = RuntimeError("load failed")

    with patch("pipeline.ollama_utils.httpx.Client", client_cls):
        with pytest.raises(RuntimeError, match="load failed"):
            ensure_model_loaded("http://localhost:11434", "qwen3:q4km")


def test_ollama_openai_base_url_is_derived_from_native_base():
    assert ollama_openai_base_url("http://ollama.internal:11434/") == (
        "http://ollama.internal:11434/v1"
    )


def test_release_model_posts_keep_alive_zero():
    with patch("pipeline.ollama_utils.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client
        release_model("http://localhost:11434", "qwen3:q4km")
        mock_client.post.assert_called_once_with(
            "http://localhost:11434/api/generate",
            json={"model": "qwen3:q4km", "keep_alive": 0},
            timeout=30.0,
        )


def test_release_model_swallows_exceptions():
    with patch("pipeline.ollama_utils.httpx.Client") as mock_client_cls:
        mock_client_cls.return_value.__enter__.side_effect = RuntimeError("连接失败")
        release_model("http://localhost:11434", "qwen3:q4km")  # 不应该抛出
