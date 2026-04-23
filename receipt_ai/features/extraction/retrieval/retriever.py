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


def _meta_epoch(meta: dict) -> int | None:
    raw = meta.get("uploaded_epoch")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _meta_str(meta: dict, *keys: str) -> str:
    for k in keys:
        v = meta.get(k)
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return ""


@dataclass(frozen=True)
class RetrievedChunk:
    file_key: str
    source_name: str
    chunk_index: int
    content: str
    score: float
    section_type: str
    document_key: str = ""
    uploaded_epoch: int | None = None
    indexed_at: str = ""


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
        expand_neighbors: bool | None = None,
    ) -> list[RetrievedChunk]:
        k = top_k if top_k is not None else max(1, self._config.rag_top_k)
        use_neighbors = self._config.rag_enable_neighbor_expansion if expand_neighbors is None else bool(expand_neighbors)
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
                expand_neighbors=use_neighbors,
            )

        all_chunks = load_all_chunk_records(self._index_root)
        candidates: list[ChunkRecord] = []
        for ch in all_chunks:
            if ch.embedding is None or len(ch.embedding) == 0:
                continue
            doc_key = str(ch.metadata.get("document_key", ch.file_key))
            if file_key_exact is not None and doc_key != file_key_exact:
                continue
            elif folder_prefix is not None and folder_prefix != "":
                prefix = folder_prefix.rstrip("/") + "/"
                if not doc_key.startswith(prefix):
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

        scored_map = {idx: s for s, idx in scored}
        best = top_k_by_score(scored, k)
        if use_neighbors:
            best = self._expand_local_neighbors(best, candidates, scored_map, k)
        out: list[RetrievedChunk] = []
        for score, idx in best:
            ch = candidates[idx]
            meta = ch.metadata or {}
            doc_key = str(meta.get("document_key", ch.file_key.split("::p", 1)[0])).strip()
            out.append(
                RetrievedChunk(
                    file_key=ch.file_key,
                    source_name=ch.source_name,
                    chunk_index=ch.chunk_index,
                    content=ch.content,
                    score=score,
                    section_type=ch.section_type,
                    document_key=doc_key,
                    uploaded_epoch=_meta_epoch(meta),
                    indexed_at=_meta_str(meta, "created_at", "indexed_at", "uploaded_at"),
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
        expand_neighbors: bool,
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
            file_key = str(meta.get("file_key", ""))
            doc_key = str(meta.get("document_key", file_key.split("::p", 1)[0])).strip()
            epoch_raw = meta.get("uploaded_epoch")
            try:
                uploaded_epoch = int(epoch_raw) if epoch_raw is not None else None
            except (TypeError, ValueError):
                uploaded_epoch = None
            out.append(
                RetrievedChunk(
                    file_key=file_key,
                    source_name=str(meta.get("source_name", "")),
                    chunk_index=chunk_index,
                    content=doc.page_content,
                    score=float(score),
                    section_type=str(meta.get("section_type", "")),
                    document_key=doc_key,
                    uploaded_epoch=uploaded_epoch,
                    indexed_at=_meta_str(meta, "uploaded_at", "indexed_at", "created_at"),
                )
            )
        return out

    def _expand_local_neighbors(
        self,
        best: list[tuple[float, int]],
        candidates: list[ChunkRecord],
        scored_map: dict[int, float],
        k: int,
    ) -> list[tuple[float, int]]:
        if not best or k <= 1:
            return best
        # Reserve space for neighbors so broad queries can keep adjacent context.
        base_take = max(1, k - 2)
        best_base = best[:base_take]
        by_doc_and_chunk: dict[tuple[str, int], int] = {}
        for i, ch in enumerate(candidates):
            meta = ch.metadata or {}
            doc_key = str(meta.get("document_key", ch.file_key.split("::p", 1)[0])).strip()
            by_doc_and_chunk[(doc_key, int(ch.chunk_index))] = i

        picked: list[tuple[float, int]] = list(best_base)
        seen = {idx for _, idx in best_base}
        for _, idx in best_base:
            ch = candidates[idx]
            meta = ch.metadata or {}
            doc_key = str(meta.get("document_key", ch.file_key.split("::p", 1)[0])).strip()
            for delta in (-1, 1):
                n_idx = by_doc_and_chunk.get((doc_key, int(ch.chunk_index) + delta))
                if n_idx is None or n_idx in seen:
                    continue
                score = float(scored_map.get(n_idx, -1.0))
                picked.append((score, n_idx))
                seen.add(n_idx)
                if len(picked) >= k:
                    break
            if len(picked) >= k:
                break
        return picked[:k]
