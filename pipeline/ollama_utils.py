from __future__ import annotations
import os

import httpx

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")


def release_model(base_url: str, model: str) -> None:
    """Best-effort: tell Ollama to unload `model` immediately. Native-only
    operation (no OpenAI-compatible equivalent) — used both to free VRAM for
    the embedding step that follows VLM parsing, and to free VRAM for the
    ingest pipeline before it starts if a chat model is still resident."""
    try:
        # trust_env=False 防止系统代理（如 SOCKS）干扰本地 Ollama 连接
        with httpx.Client(trust_env=False) as c:
            c.post(f"{base_url}/api/generate", json={"model": model, "keep_alive": 0}, timeout=30.0)
    except Exception:
        pass
