from __future__ import annotations

_MODEL_CACHE = None


class Embedder:
    """BGE-M3 dense embedder. Model weights are loaded once at class level."""

    MODEL_NAME = "BAAI/bge-m3"

    @classmethod
    def _get_model(cls):
        global _MODEL_CACHE
        if _MODEL_CACHE is None:
            from FlagEmbedding import BGEM3FlagModel
            _MODEL_CACHE = BGEM3FlagModel(cls.MODEL_NAME, use_fp16=True)
        return _MODEL_CACHE

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
