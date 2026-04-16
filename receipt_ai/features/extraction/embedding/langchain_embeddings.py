from __future__ import annotations

from langchain_core.embeddings import Embeddings

from receipt_ai.features.extraction.embedding.fastembed_provider import FastEmbedProvider


class FastEmbedLangChainEmbeddings(Embeddings):
    """LangChain `Embeddings` adapter around `FastEmbedProvider` (same vectors as JSON index)."""

    def __init__(self, provider: FastEmbedProvider) -> None:
        self._provider = provider

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._provider.embed_batch(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._provider.embed_query(text)
