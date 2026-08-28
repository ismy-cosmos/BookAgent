"""
视觉健全性检查：验证模型能处理图像输入且推理驻留 GPU。

用法：
    python -m pipeline.agent.check_vision --models qwen3:q4km qwen3:q5ks
    python -m pipeline.agent.check_vision --image /path/to/test.png
"""
from __future__ import annotations

import argparse
import base64
import io
import sys
import time
from typing import Optional

import httpx
from openai import OpenAI, OpenAIError

from pipeline.parse.image import describe_image

try:
    from PIL import Image, ImageDraw
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

_PASS_LATENCY_S = 60.0


def _create_test_image() -> bytes:
    if not _PIL_AVAILABLE:
        # Minimal 1×1 red pixel PNG (hardcoded bytes, no URL)
        _RED_1X1_PNG = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
            b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
            b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        return _RED_1X1_PNG
    img = Image.new("RGB", (200, 100), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((20, 35), "VISION TEST 42", fill="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _model_vram_residency(model: str, ollama_base: str) -> Optional[bool]:
    """Query Ollama's /api/ps for `model`: True if fully resident in VRAM
    (size_vram >= size), False if partially/not resident, None if unknown
    (model not in the running list, or /api/ps unreachable)."""
    try:
        resp = httpx.get(f"{ollama_base}/api/ps", timeout=10.0)
        resp.raise_for_status()
    except httpx.HTTPError:
        return None
    for m in resp.json().get("models", []):
        if m.get("model") == model:
            size = m.get("size")
            size_vram = m.get("size_vram")
            if size and size_vram is not None:
                return size_vram >= size
    return None


def _check_model(model: str, image_bytes: bytes, ollama_base: str) -> bool:
    b64 = base64.b64encode(image_bytes).decode()
    client = OpenAI(base_url=f"{ollama_base}/v1", api_key="ollama", timeout=120.0)

    t0 = time.perf_counter()
    try:
        answer = describe_image(
            client, model, b64,
            prompt="Describe what you see in this image in one sentence.",
        )
    except (OpenAIError, ValueError) as e:
        print(f"  ✗ Vision call failed: {e}")
        return False

    latency = time.perf_counter() - t0
    gpu_resident = _model_vram_residency(model, ollama_base)
    ok = True

    print(f"  Response     : {answer[:120]}")
    print(f"  Latency      : {latency:.1f}s  (limit {_PASS_LATENCY_S}s)")
    print(f"  GPU resident : {gpu_resident}  (via /api/ps size_vram >= size)")

    if latency > _PASS_LATENCY_S:
        print(f"  ✗ Latency too high — likely CPU fallback")
        ok = False
    if gpu_resident is not True:
        print(f"  ✗ Model not confirmed fully GPU-resident")
        ok = False

    return ok


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Vision sanity check")
    parser.add_argument("--models", nargs="+",
                        default=["qwen3:q4km", "qwen3:q5ks"])
    parser.add_argument("--image", help="Test image path (default: auto-generate)")
    parser.add_argument("--ollama-base", default="http://localhost:11434")
    args = parser.parse_args(argv)

    if args.image:
        with open(args.image, "rb") as f:
            image_bytes = f.read()
        print(f"Using image: {args.image}")
    else:
        image_bytes = _create_test_image()
        print("Auto-generated test image (200×100, 'VISION TEST 42')")

    results: dict[str, bool] = {}
    for model in args.models:
        print(f"\nChecking {model} ...")
        results[model] = _check_model(model, image_bytes, args.ollama_base)
        print(f"  → {'✓ PASS' if results[model] else '✗ FAIL'}")

    failed = [m for m, ok in results.items() if not ok]
    if failed:
        print(f"\nFailed: {failed}")
        print("Fix: reduce num_ctx / n_gpu_layers in Modelfile, rebuild, retry.")
        sys.exit(1)

    print("\nAll models passed. Proceed to tool-calling verification.")


if __name__ == "__main__":
    main()
