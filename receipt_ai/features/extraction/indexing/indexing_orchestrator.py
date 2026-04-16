from __future__ import annotations

from dataclasses import dataclass
import logging
import time

from receipt_ai.features.extraction.chunking import (
    ChunkBuildInput,
    build_chunks,
    normalize_extracted_text,
    segment_text_for_chunking,
)
from receipt_ai.features.extraction.config import ExtractionConfig
from receipt_ai.features.extraction.embedding import FastEmbedProvider
from receipt_ai.features.extraction.indexing.chunk_repository import ChunkRepository
from receipt_ai.features.extraction.indexing import qdrant_index

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IndexingRequest:
    file_key: str
    folder: str
    filename: str
    extracted_text: str
    doc_type: str


class IndexingOrchestrator:
    def __init__(self, config: ExtractionConfig | None = None) -> None:
        self._config = config or ExtractionConfig.from_env()
        self._repo = ChunkRepository(self._config)
        self._embedder = FastEmbedProvider(self._config)

    def process(self, request: IndexingRequest) -> str:
        if self._repo.get_status(request.file_key) == "processing":
            logger.info("indexing_skip_duplicate file_key=%s", request.file_key)
            return ""

        self._repo.set_status(request.file_key, "processing")
        started = time.perf_counter()
        try:
            normalized = normalize_extracted_text(request.extracted_text)
            segments = segment_text_for_chunking(normalized, request.filename)
            chunks = build_chunks(
                ChunkBuildInput(
                    file_key=request.file_key,
                    source_name=request.filename,
                    doc_type=request.doc_type,
                    segments=segments,
                ),
                self._config,
            )
            if not chunks:
                self._repo.set_status(request.file_key, "failed", reason="No useful chunks were produced.")
                return ""

            texts = [chunk.content for chunk in chunks]
            vectors = self._embed_with_retries(texts)
            if len(vectors) != len(chunks):
                self._repo.set_status(request.file_key, "failed", reason="Embedding count mismatch.")
                return ""

            for i, chunk in enumerate(chunks):
                chunk.embedding = vectors[i]
                chunk.metadata["embedding_dim"] = len(vectors[i])

            output = self._repo.save_chunks(request.folder, request.filename, chunks)
            if qdrant_index.qdrant_enabled(self._config):
                qdrant_index.upsert_chunks_for_file(self._config, self._embedder, request, chunks)
            self._repo.set_status(request.file_key, "completed")
            elapsed = int((time.perf_counter() - started) * 1000)
            logger.info(
                "indexing_success file_key=%s chunk_count=%s duration_ms=%s output=%s",
                request.file_key,
                len(chunks),
                elapsed,
                output,
            )
            return output
        except Exception as exc:
            self._repo.set_status(request.file_key, "failed", reason=str(exc))
            logger.exception("indexing_failed file_key=%s", request.file_key)
            return ""

    def _embed_with_retries(self, texts: list[str]) -> list[list[float]]:
        retries = max(0, self._config.embedding_max_retries)
        batch_size = max(1, self._config.embedding_batch_size)
        last_exc: Exception | None = None
        for attempt in range(retries + 1):
            try:
                vectors: list[list[float]] = []
                for start in range(0, len(texts), batch_size):
                    batch = texts[start : start + batch_size]
                    vectors.extend(self._embedder.embed_batch(batch))
                return vectors
            except Exception as exc:
                last_exc = exc
                logger.warning("embedding_retry attempt=%s error=%s", attempt + 1, exc)
        if last_exc:
            raise last_exc
        return []
