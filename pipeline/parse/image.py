from __future__ import annotations
import base64
import os
from pathlib import Path
from typing import Optional

import httpx
from openai import OpenAI, OpenAIError

from pipeline.parse.base import Element

_OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
_VLM_MODEL = os.environ.get("VLM_MODEL", "qwen3:q4km")
_DESCRIBE_PROMPT = (
    "Describe all content visible in this image in detail. "
    "Include any text, formulas, diagrams, tables, and figures. "
    "Respond in the same language as the text in the image."
)


def describe_image(
    client: OpenAI,
    model: str,
    b64_png: str,
    prompt: str = _DESCRIBE_PROMPT,
    options: Optional[dict] = None,
    keep_alive: int = 1200,
) -> str:
    """Send a base64 PNG to an Ollama vision model via the OpenAI-compatible endpoint."""
    response = client.chat.completions.create(
        model=model,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_png}"}},
            ],
        }],
        extra_body={"options": options or {}, "keep_alive": keep_alive},
    )
    content = response.choices[0].message.content
    if not content:
        raise ValueError(f"Unexpected Ollama response format: empty content (model={model})")
    return content.strip()


class VLMImageParser:
    """Describe images using a local Ollama vision model via the openai SDK."""

    def __init__(
        self,
        model: str = _VLM_MODEL,
        ollama_base: str = _OLLAMA_BASE,
        timeout: float = 120.0,
    ):
        self._model = model
        self._base = ollama_base.rstrip("/")
        self._openai = OpenAI(
            base_url=f"{self._base}/v1",
            api_key="ollama",
            http_client=httpx.Client(trust_env=False),
            timeout=timeout,
        )

    def parse(self, image_path: str) -> list[Element]:
        if not Path(image_path).exists():
            raise ValueError(f"File not found: {image_path}")
        img_bytes = self._load_as_png_bytes(image_path)
        b64 = base64.b64encode(img_bytes).decode()
        try:
            description = describe_image(self._openai, self._model, b64)
        except OpenAIError as e:
            raise ValueError(f"Ollama vision call failed: {e}") from e
        return [Element(type="figure", content=description, page_num=0)]

    def _load_as_png_bytes(self, image_path: str) -> bytes:
        path = Path(image_path)
        if path.suffix.lower() == ".svg":
            try:
                import cairosvg
                return cairosvg.svg2png(url=str(path))
            except Exception as e:
                raise ValueError(f"SVG conversion failed for {image_path}: {e}") from e
        return path.read_bytes()