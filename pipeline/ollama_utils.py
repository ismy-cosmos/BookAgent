from __future__ import annotations
import os
from typing import Any

import httpx

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
_MODEL_PROBE_TIMEOUT_S = 10.0
_MODEL_LOAD_TIMEOUT_S = 120.0


def _native_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}{path}"


def ollama_openai_base_url(base_url: str = OLLAMA_BASE_URL) -> str:
    """Derive Ollama's OpenAI-compatible endpoint from its native base URL."""
    return _native_url(base_url, "/v1")


def _loaded_models(payload: Any) -> list[dict]:
    if not isinstance(payload, dict) or not isinstance(payload.get("models"), list):
        raise ValueError("Ollama /api/ps 返回格式无效：缺少 models 列表")
    models = payload["models"]
    if not all(isinstance(item, dict) for item in models):
        raise ValueError("Ollama /api/ps 返回格式无效：models 条目不是对象")
    return models


def ensure_model_loaded(base_url: str, model: str) -> None:
    """Synchronously ensure `model` is resident before a real answer starts.

    A successful /api/ps response that does not contain the target model is
    followed by Ollama's documented empty generation request. Probe, HTTP,
    timeout and response-shape failures deliberately propagate to the /ask
    route, which maps them to the existing local-model 503 response.
    """
    with httpx.Client(trust_env=False) as client:
        response = client.get(
            _native_url(base_url, "/api/ps"),
            timeout=_MODEL_PROBE_TIMEOUT_S,
        )
        response.raise_for_status()
        loaded = any(
            item.get("name") == model or item.get("model") == model
            for item in _loaded_models(response.json())
        )
        if loaded:
            return

        response = client.post(
            _native_url(base_url, "/api/generate"),
            json={"model": model, "stream": False},
            timeout=_MODEL_LOAD_TIMEOUT_S,
        )
        response.raise_for_status()


def release_model(base_url: str, model: str) -> None:
    """Best-effort: tell Ollama to unload `model` immediately. Native-only
    operation (no OpenAI-compatible equivalent) — used both to free VRAM for
    the embedding step that follows VLM parsing, and to free VRAM for the
    ingest pipeline before it starts if a chat model is still resident."""
    try:
        # trust_env=False 防止系统代理（如 SOCKS）干扰本地 Ollama 连接
        with httpx.Client(trust_env=False) as c:
            c.post(
                _native_url(base_url, "/api/generate"),
                json={"model": model, "keep_alive": 0},
                timeout=30.0,
            )
    except Exception:
        pass
