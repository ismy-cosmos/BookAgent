"""Shared surya-OCR wrapper for figure degradation and ablation branches.

Lazy-loads DetectionPredictor + RecognitionPredictor once, reuses across calls.
GPU paths must call release_ocr_models() after the batch is complete.

Usage:
    from pipeline.parse.surya_ocr import ocr_image, release_ocr_models
    text = ocr_image(image_bytes, device="cpu")
    # ... after batch ...
    release_ocr_models()
"""
from __future__ import annotations
import io
import os
from typing import Optional

from PIL import Image

_SURYA_DEVICE = os.environ.get("SURYA_DEVICE", "cpu")

_det_predictor = None
_rec_predictor = None


def _get_device(device: str | None) -> str:
    return device or _SURYA_DEVICE


def _get_predictors(device: str):
    global _det_predictor, _rec_predictor
    if _det_predictor is None:
        import torch
        from surya.detection import DetectionPredictor
        _det_predictor = DetectionPredictor(
            device=device,
            dtype=torch.float16 if device == "cuda" else torch.float32,
        )
    if _rec_predictor is None:
        import torch
        from surya.recognition import RecognitionPredictor
        _rec_predictor = RecognitionPredictor(
            device=device,
            dtype=torch.float16 if device == "cuda" else torch.float32,
        )
    return _det_predictor, _rec_predictor


def ocr_image(image_bytes: bytes, device: str | None = None) -> str:
    """Run surya OCR on a single image (PNG/JPEG bytes), return extracted text.

    Returns empty string if no text detected or OCR fails.
    """
    dev = _get_device(device)
    det, rec = _get_predictors(dev)

    img = Image.open(io.BytesIO(image_bytes))
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    try:
        result = rec([img], [None], det_predictor=det, highres_images=[img])
    except Exception:
        return ""

    text_lines = result[0].text_lines
    if not text_lines:
        return ""

    return " ".join(line.text for line in text_lines)


def release_ocr_models() -> None:
    """Release surya OCR models and free GPU memory (idempotent)."""
    global _det_predictor, _rec_predictor
    _det_predictor = None
    _rec_predictor = None
    import gc
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass
