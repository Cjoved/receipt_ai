from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from receipt_ai.features.extraction.chunking.models import ChunkRecord
from receipt_ai.features.extraction.config import ExtractionConfig
from receipt_ai.features.extraction.embedding.fastembed_provider import FastEmbedProvider
from receipt_ai.features.extraction.indexing.qdrant_index import (
    build_qdrant_filter,
    get_qdrant_vector_store,
    qdrant_enabled,
)
from receipt_ai.features.extraction.retrieval.chunk_json import load_all_chunk_records
from receipt_ai.features.extraction.retrieval.similarity import cosine_similarity, top_k_by_score


@dataclass(frozen=True)
class RetrievedChunk:
    file_key: str
    source_name: str
    chunk_index: int
    content: str
    score: float
    section_type: str


class ChunkRetriever:
    def __init__(self, config: ExtractionConfig | None = None) -> None:
        self._config = config or ExtractionConfig.from_env()
        self._embedder = FastEmbedProvider(self._config)
        self._index_root = Path(self._config.index_output_dir)

    def retrieve(
        self,
        query: str,
        *,
        top_k: int | None = None,
        folder_prefix: str | None = None,
        file_key_exact: str | None = None,
        file_type_exact: str | None = None,
    ) -> list[RetrievedChunk]:
        k = top_k if top_k is not None else max(1, self._config.rag_top_k)
        query = query.strip()
        if not query:
            return []

        if qdrant_enabled(self._config):
            return self._retrieve_from_qdrant(
                query,
                top_k=k,
                folder_prefix=folder_prefix,
                file_key_exact=file_key_exact,
                file_type_exact=file_type_exact,
            )

        all_chunks = load_all_chunk_records(self._index_root)
        candidates: list[ChunkRecord] = []
        for ch in all_chunks:
            if ch.embedding is None or len(ch.embedding) == 0:
                continue
            if file_key_exact is not None and ch.file_key != file_key_exact:
                continue
            elif folder_prefix is not None and folder_prefix != "":
                prefix = folder_prefix.rstrip("/") + "/"
                if not ch.file_key.startswith(prefix):
                    continue
            if file_type_exact:
                chunk_file_type = str(ch.metadata.get("file_type", ch.metadata.get("doc_type", ""))).strip().lower()
                if chunk_file_type != file_type_exact.strip().lower():
                    continue
            candidates.append(ch)

        if not candidates:
            return []

        q_vec = self._embedder.embed_query(query)
        if not q_vec:
            return []

        scored: list[tuple[float, int]] = []
        for i, ch in enumerate(candidates):
            emb = ch.embedding or []
            scored.append((cosine_similarity(q_vec, emb), i))

        best = top_k_by_score(scored, k)
        out: list[RetrievedChunk] = []
        for score, idx in best:
            ch = candidates[idx]
            out.append(
                RetrievedChunk(
                    file_key=ch.file_key,
                    source_name=ch.source_name,
                    chunk_index=ch.chunk_index,
                    content=ch.content,
                    score=score,
                    section_type=ch.section_type,
                )
            )
        return out

    def _retrieve_from_qdrant(
        self,
        query: str,
        *,
        top_k: int,
        folder_prefix: str | None,
        file_key_exact: str | None,
        file_type_exact: str | None,
    ) -> list[RetrievedChunk]:
        """Semantic search via LangChain `QdrantVectorStore.similarity_search_with_score`."""
        q_filter = build_qdrant_filter(
            folder_prefix=folder_prefix,
            file_key_exact=file_key_exact,
            file_type_exact=file_type_exact,
        )
        store, _ = get_qdrant_vector_store(self._config, self._embedder)
        pairs = store.similarity_search_with_score(query, k=top_k, filter=q_filter)
        out: list[RetrievedChunk] = []
        for doc, score in pairs:
            meta = doc.metadata or {}
            try:
                chunk_index = int(meta.get("chunk_index", 0))
            except (TypeError, ValueError):
                chunk_index = 0
            out.append(
                RetrievedChunk(
                    file_key=str(meta.get("file_key", "")),
                    source_name=str(meta.get("source_name", "")),
                    chunk_index=chunk_index,
                    content=doc.page_content,
                    score=float(score),
                    section_type=str(meta.get("section_type", "")),
                )
            )
        return out
