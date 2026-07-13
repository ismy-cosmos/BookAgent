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


def release_gpu_model() -> None:
    """释放 GPU 常驻的 embedder（device=None 缓存键 "auto"）。

    导入任务结束后调用——模型加载后没有任何自动过期机制，会一直占着显存，
    跟 Ollama 后续加载模型抢显存，抢不到时 Ollama 会把部分层（包括多模态
    投影层）退到 CPU，拖慢速度。device="cpu" 那份查询用的缓存不动，本来就
    不占显存。释放后下次导入需要重新加载模型（几秒延迟），用这点延迟换
    显存余量。
    """
    with _MODEL_LOCK:
        model = _MODEL_CACHE.pop("auto", None)
    if model is None:
        return
    del model
    import gc
    gc.collect()
    # torch 是 FlagEmbedding 的硬依赖——能走到这里说明模型已经加载过，
    # torch 必然已经装了，不需要 try/except ImportError 兜底。
    import torch
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
