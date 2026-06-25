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
import subprocess
import sys
import time

import httpx

try:
    from PIL import Image, ImageDraw
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

_PASS_VRAM_MIB = 4000
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


def _get_vram_free_mib() -> int | None:
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.free",
             "--format=csv,noheader,nounits"],
            text=True, timeout=5,
        )
        return int(out.strip().split("\n")[0])
    except Exception:
        return None


def _check_model(model: str, image_bytes: bytes, ollama_base: str) -> bool:
    b64 = base64.b64encode(image_bytes).decode()
    vram_before = _get_vram_free_mib()

    t0 = time.perf_counter()
    try:
        resp = httpx.post(
            f"{ollama_base}/api/chat",
            json={
                "model": model,
                "messages": [{
                    "role": "user",
                    "content": "Describe what you see in this image in one sentence.",
                    "images": [b64],
                }],
                "stream": False,
                "keep_alive": 1200,
            },
            timeout=120.0,
        )
    except httpx.ConnectError as e:
        print(f"  ✗ Cannot connect to Ollama: {e}")
        return False

    latency = time.perf_counter() - t0
    vram_after = _get_vram_free_mib()

    if resp.status_code != 200:
        print(f"  ✗ HTTP {resp.status_code}: {resp.text[:200]}")
        return False

    answer = resp.json().get("message", {}).get("content", "").strip()
    ok = True

    print(f"  Response : {answer[:120]}")
    print(f"  Latency  : {latency:.1f}s  (limit {_PASS_LATENCY_S}s)")
    print(f"  VRAM free: {vram_before} → {vram_after} MiB  (limit >{_PASS_VRAM_MIB})")

    if not answer:
        print("  ✗ Empty response")
        ok = False
    if latency > _PASS_LATENCY_S:
        print(f"  ✗ Latency too high — likely CPU fallback")
        ok = False
    if vram_after is not None and vram_after < _PASS_VRAM_MIB:
        print(f"  ✗ VRAM free too low — model not GPU-resident")
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
