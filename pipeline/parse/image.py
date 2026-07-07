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

# 真实 GPU 实测（qwen3:q4km，每尺寸独立测、测前后显式释放）：
# 长边 2048px 正常（2772 token），3072px 起视觉编码阶段 cudaMalloc OOM。
# 与 num_ctx 无关——那是文本 token 预算，这里是图像张量的显存开销。
_MAX_IMAGE_DIM = 2048


def _resize_to_limit(img_bytes: bytes, max_dim: int = _MAX_IMAGE_DIM) -> bytes:
    """长边超过 max_dim 时等比缩小并重编码 PNG；否则原样返回。
    无法解析的字节原样透传——resize 是安全网，不是准入门槛。"""
    import io
    from PIL import Image, UnidentifiedImageError
    try:
        img = Image.open(io.BytesIO(img_bytes))
        img.load()
    except (UnidentifiedImageError, OSError):
        return img_bytes
    w, h = img.size
    if max(w, h) <= max_dim:
        return img_bytes
    scale = max_dim / max(w, h)
    resized = img.resize((max(1, round(w * scale)), max(1, round(h * scale))))
    if resized.mode not in ("RGB", "RGBA", "L", "LA"):
        resized = resized.convert("RGB")
    buf = io.BytesIO()
    resized.save(buf, format="PNG")
    return buf.getvalue()


def _load_as_png_bytes(image_path: str) -> bytes:
    path = Path(image_path)
    if path.suffix.lower() == ".svg":
        try:
            import cairosvg
            return cairosvg.svg2png(url=str(path))
        except Exception as e:
            raise ValueError(f"SVG conversion failed for {image_path}: {e}") from e
    return path.read_bytes()


def load_image_element(image_path: str) -> Element:
    """把独立图片文件读成带真实字节的 figure Element，不调 VLM。
    描述在 ingest 的 VLM 批量阶段统一生成。"""
    if not Path(image_path).exists():
        raise ValueError(f"File not found: {image_path}")
    img_bytes = _load_as_png_bytes(image_path)
    return Element(
        type="figure",
        content=f"![]({Path(image_path).name})",
        page_num=0,
        metadata={"image_bytes": img_bytes},
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


def _release_model(base_url: str, model: str) -> None:
    """Best-effort: tell Ollama to unload `model` immediately. Native-only
    operation (no OpenAI-compatible equivalent) — frees VRAM for the
    embedding step that follows VLM parsing in the ingest pipeline."""
    try:
        httpx.post(f"{base_url}/api/generate", json={"model": model, "keep_alive": 0}, timeout=30.0)
    except httpx.HTTPError:
        pass


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
        img_bytes = _resize_to_limit(_load_as_png_bytes(image_path))
        b64 = base64.b64encode(img_bytes).decode()
        try:
            description = describe_image(self._openai, self._model, b64)
        except OpenAIError as e:
            raise ValueError(f"Ollama vision call failed: {e}") from e
        finally:
            _release_model(self._base, self._model)
        return [Element(type="figure", content=description, page_num=0)]