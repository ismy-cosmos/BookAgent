from unittest.mock import patch, MagicMock

from pipeline.ollama_utils import release_model


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
