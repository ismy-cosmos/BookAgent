from __future__ import annotations
import threading
from typing import Optional

_MODEL_CACHE: dict[str, object] = {}
_MODEL_LOCK = threading.Lock()


class Embedder:
    """BGE-M3 dense embedder. Model weights are loaded once per device, cached at module level.

    device=None (default) lets FlagEmbedding auto-detect (GPU if available) — used by ingest.py's
    batch encoding, where GPU throughput matters (~24x faster than CPU for batches of chunks).
    device="cpu" is for single-query use (e.g. RealExecutor.retrieve) where a query embeds in
    ~0.3s on CPU regardless, and staying off GPU leaves that VRAM for the LLM.
    """

    MODEL_NAME = "BAAI/bge-m3"

    def __init__(self, device: Optional[str] = None) -> None:
        self._device = device

    def _get_model(self):
        key = self._device or "auto"
        if key not in _MODEL_CACHE:
            with _MODEL_LOCK:
                if key not in _MODEL_CACHE:
                    from FlagEmbedding import BGEM3FlagModel
                    kwargs = {"use_fp16": True}
                    if self._device is not None:
                        kwargs["devices"] = self._device
                    _MODEL_CACHE[key] = BGEM3FlagModel(self.MODEL_NAME, **kwargs)
        return _MODEL_CACHE[key]

    def embed(self, texts: list[str]) -> list[list[float]]:
        model = self._get_model()
        result = model.encode(
            texts,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False,
        )
        return [vec.tolist() for vec in result["dense_vecs"]]

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]
