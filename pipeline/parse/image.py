from __future__ import annotations
import base64
import os
from pathlib import Path

import httpx

from pipeline.parse.base import Element

_OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
_VLM_MODEL = os.environ.get("VLM_MODEL", "qwen3:q4km")
_DESCRIBE_PROMPT = (
    "Describe all content visible in this image in detail. "
    "Include any text, formulas, diagrams, tables, and figures. "
    "Respond in the same language as the text in the image."
)


class VLMImageParser:
    """Describe images using a local Ollama vision model."""

    def __init__(
        self,
        model: str = _VLM_MODEL,
        ollama_base: str = _OLLAMA_BASE,
        timeout: float = 120.0,
    ):
        self._model = model
        self._base = ollama_base.rstrip("/")
        self._timeout = timeout

    def parse(self, image_path: str) -> list[Element]:
        img_bytes = self._load_as_png_bytes(image_path)
        b64 = base64.b64encode(img_bytes).decode()
        resp = httpx.post(
            f"{self._base}/api/chat",
            json={
                "model": self._model,
                "messages": [{
                    "role": "user",
                    "content": _DESCRIBE_PROMPT,
                    "images": [b64],
                }],
                "stream": False,
                "keep_alive": 1200,
            },
            timeout=self._timeout,
        )
        resp.raise_for_status()
        description = resp.json()["message"]["content"].strip()
        return [Element(type="figure", content=description, page_num=0)]

    def _load_as_png_bytes(self, image_path: str) -> bytes:
        path = Path(image_path)
        if path.suffix.lower() == ".svg":
            import cairosvg
            return cairosvg.svg2png(url=str(path))
        return path.read_bytes()
