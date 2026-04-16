from __future__ import annotations

from fastembed import TextEmbedding

from receipt_ai.features.extraction.config import ExtractionConfig


class FastEmbedProvider:
    def __init__(self, config: ExtractionConfig) -> None:
        self._config = config
        self._model = TextEmbedding(model_name=config.embedding_model)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for vector in self._model.embed(texts):
            vectors.append(vector.tolist())
        return vectors

    def embed_query(self, text: str) -> list[float]:
        batch = self.embed_batch([text])
        return batch[0] if batch else []
