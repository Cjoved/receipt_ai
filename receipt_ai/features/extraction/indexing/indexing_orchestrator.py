from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import threading
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
_DEBUG_LOG_PATH = "debug-fa7c0f.log"
_DEBUG_SESSION_ID = "fa7c0f"


def _agent_debug_log(location: str, message: str, data: dict, *, run_id: str, hypothesis_id: str) -> None:
    entry = {
        "sessionId": _DEBUG_SESSION_ID,
        "id": f"log_{time.time_ns()}",
        "timestamp": int(time.time() * 1000),
        "location": location,
        "message": message,
        "data": data,
        "runId": run_id,
        "hypothesisId": hypothesis_id,
    }
    try:
        with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


@dataclass(frozen=True)
class IndexingRequest:
    file_key: str
    folder: str
    filename: str
    extracted_text: str
    doc_type: str
    cancel_event: threading.Event | None = None


class IndexingCancelledError(Exception):
    """Raised when upload stop is requested while indexing is running."""


class IndexingOrchestrator:
    def __init__(self, config: ExtractionConfig | None = None) -> None:
        self._config = config or ExtractionConfig.from_env()
        self._repo = ChunkRepository(self._config)
        self._embedder = FastEmbedProvider(self._config)

    def process(self, request: IndexingRequest) -> str:
        # #region agent log
        _agent_debug_log(
            "indexing_orchestrator.py:process:start",
            "Indexing started",
            {
                "file_key": request.file_key,
                "cancel_event_set": (request.cancel_event.is_set() if request.cancel_event is not None else None),
                "qdrant_enabled": bool(qdrant_index.qdrant_enabled(self._config)),
                "qdrant_url_present": bool(self._config.qdrant_url.strip()),
                "qdrant_collection": self._config.qdrant_collection,
            },
            run_id="qdrant-debug",
            hypothesis_id="Q1",
        )
        # #endregion
        self._raise_if_cancelled(request)
        claimed, recovered_stale = self._repo.begin_processing(
            request.file_key,
            stale_after_seconds=self._config.indexing_processing_stale_seconds,
        )
        if not claimed:
            logger.info("indexing_skip_duplicate file_key=%s", request.file_key)
            # #region agent log
            _agent_debug_log(
                "indexing_orchestrator.py:process:skip_duplicate",
                "Skipped duplicate processing",
                {"file_key": request.file_key},
                run_id="qdrant-debug",
                hypothesis_id="Q4",
            )
            # #endregion
            return ""
        if recovered_stale:
            logger.warning("indexing_recovered_stale_processing file_key=%s", request.file_key)
            _agent_debug_log(
                "indexing_orchestrator.py:process:stale_recovered",
                "Recovered stale processing lock",
                {
                    "file_key": request.file_key,
                    "stale_after_seconds": self._config.indexing_processing_stale_seconds,
                },
                run_id="qdrant-debug",
                hypothesis_id="Q7",
            )

        started = time.perf_counter()
        try:
            self._raise_if_cancelled(request)
            normalized = normalize_extracted_text(request.extracted_text)
            self._raise_if_cancelled(request)
            segments = segment_text_for_chunking(normalized, request.filename)
            self._raise_if_cancelled(request)
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
            vectors = self._embed_with_retries(request, texts)
            if len(vectors) != len(chunks):
                self._repo.set_status(request.file_key, "failed", reason="Embedding count mismatch.")
                return ""

            for i, chunk in enumerate(chunks):
                self._raise_if_cancelled(request)
                chunk.embedding = vectors[i]
                chunk.metadata["embedding_dim"] = len(vectors[i])

            self._raise_if_cancelled(request)
            output = self._repo.save_chunks(request.folder, request.filename, chunks)
            if not qdrant_index.qdrant_enabled(self._config):
                raise RuntimeError("Qdrant is required but QDRANT_URL is missing.")
            self._raise_if_cancelled(request)
            # #region agent log
            _agent_debug_log(
                "indexing_orchestrator.py:process:before_qdrant_upsert",
                "About to upsert chunks to qdrant",
                {"file_key": request.file_key, "chunk_count": len(chunks)},
                run_id="qdrant-debug",
                hypothesis_id="Q2",
            )
            # #endregion
            qdrant_index.upsert_chunks_for_file(self._config, self._embedder, request, chunks)
            self._repo.set_status(request.file_key, "completed")
            elapsed = int((time.perf_counter() - started) * 1000)
            # #region agent log
            _agent_debug_log(
                "indexing_orchestrator.py:process:completed",
                "Indexing completed",
                {"file_key": request.file_key, "duration_ms": elapsed},
                run_id="qdrant-debug",
                hypothesis_id="Q3",
            )
            # #endregion
            logger.info(
                "indexing_success file_key=%s chunk_count=%s duration_ms=%s output=%s",
                request.file_key,
                len(chunks),
                elapsed,
                output,
            )
            return output
        except IndexingCancelledError:
            self._repo.set_status(request.file_key, "cancelled", reason="Stopped by user.")
            # #region agent log
            _agent_debug_log(
                "indexing_orchestrator.py:process:cancelled",
                "Indexing cancelled",
                {"file_key": request.file_key},
                run_id="qdrant-debug",
                hypothesis_id="Q5",
            )
            # #endregion
            logger.info("indexing_cancelled file_key=%s", request.file_key)
            return ""
        except Exception as exc:
            self._repo.set_status(request.file_key, "failed", reason=str(exc))
            # #region agent log
            _agent_debug_log(
                "indexing_orchestrator.py:process:failed",
                "Indexing failed",
                {"file_key": request.file_key, "error": str(exc)},
                run_id="qdrant-debug",
                hypothesis_id="Q6",
            )
            # #endregion
            logger.exception("indexing_failed file_key=%s", request.file_key)
            return ""

    def _embed_with_retries(self, request: IndexingRequest, texts: list[str]) -> list[list[float]]:
        retries = max(0, self._config.embedding_max_retries)
        batch_size = max(1, self._config.embedding_batch_size)
        last_exc: Exception | None = None
        for attempt in range(retries + 1):
            try:
                self._raise_if_cancelled(request)
                vectors: list[list[float]] = []
                for start in range(0, len(texts), batch_size):
                    self._raise_if_cancelled(request)
                    batch = texts[start : start + batch_size]
                    vectors.extend(self._embedder.embed_batch(batch))
                return vectors
            except Exception as exc:
                last_exc = exc
                logger.warning("embedding_retry attempt=%s error=%s", attempt + 1, exc)
        if last_exc:
            raise last_exc
        return []

    def _raise_if_cancelled(self, request: IndexingRequest) -> None:
        ev = request.cancel_event
        if ev is not None and ev.is_set():
            raise IndexingCancelledError("Stopped by user.")
