from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore, RetrievalMode
from qdrant_client import QdrantClient
from qdrant_client.http import models

from receipt_ai.features.extraction.config import ExtractionConfig
from receipt_ai.features.extraction.embedding.fastembed_provider import FastEmbedProvider
from receipt_ai.features.extraction.embedding.langchain_embeddings import FastEmbedLangChainEmbeddings

if TYPE_CHECKING:
    from receipt_ai.features.extraction.chunking.models import ChunkRecord
    from receipt_ai.features.extraction.indexing.indexing_orchestrator import IndexingRequest

logger = logging.getLogger(__name__)


def qdrant_enabled(config: ExtractionConfig) -> bool:
    return bool(config.qdrant_url and config.qdrant_url.strip())


def _make_client(config: ExtractionConfig) -> QdrantClient:
    kwargs: dict = {"url": config.qdrant_url.strip()}
    if config.qdrant_api_key:
        kwargs["api_key"] = config.qdrant_api_key
    return QdrantClient(**kwargs)


def ensure_collection(client: QdrantClient, collection_name: str, vector_size: int) -> None:
    if client.collection_exists(collection_name=collection_name):
        return
    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
    )
    logger.info("qdrant_collection_created name=%s dim=%s", collection_name, vector_size)


def get_qdrant_vector_store(
    config: ExtractionConfig,
    embed_provider: FastEmbedProvider,
) -> tuple[QdrantVectorStore, QdrantClient]:
    """Return a `QdrantVectorStore` + client; creates collection if missing."""
    client = _make_client(config)
    lc_emb = FastEmbedLangChainEmbeddings(embed_provider)
    dim = len(lc_emb.embed_query("dimension_probe"))
    ensure_collection(client, config.qdrant_collection, dim)
    store = QdrantVectorStore(
        client=client,
        collection_name=config.qdrant_collection,
        embedding=lc_emb,
        retrieval_mode=RetrievalMode.DENSE,
    )
    return store, client


def delete_points_for_file_key(client: QdrantClient, collection_name: str, file_key: str) -> None:
    """Remove all points whose LangChain payload metadata matches `file_key` (re-index)."""
    client.delete(
        collection_name=collection_name,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="metadata.file_key",
                        match=models.MatchValue(value=file_key),
                    )
                ]
            )
        ),
    )


def upsert_chunks_for_file(
    config: ExtractionConfig,
    embed_provider: FastEmbedProvider,
    request: "IndexingRequest",
    chunks: list["ChunkRecord"],
) -> None:
    """Write chunk vectors + text to Qdrant using LangChain `Document` + `add_documents`."""
    if not chunks:
        return
    store, client = get_qdrant_vector_store(config, embed_provider)
    delete_points_for_file_key(client, config.qdrant_collection, request.file_key)

    documents: list[Document] = []
    ids: list[str] = []
    for ch in chunks:
        documents.append(
            Document(
                page_content=ch.content,
                metadata={
                    "file_key": request.file_key,
                    "folder": request.folder,
                    "source_name": request.filename,
                    "chunk_index": ch.chunk_index,
                    "section_type": ch.section_type,
                },
            )
        )
        ids.append(str(uuid.uuid5(uuid.NAMESPACE_URL, f"{request.file_key}:{ch.chunk_index}")))

    store.add_documents(documents=documents, ids=ids)
    logger.info(
        "qdrant_upsert file_key=%s points=%s collection=%s",
        request.file_key,
        len(ids),
        config.qdrant_collection,
    )


def build_qdrant_filter(
    *,
    folder_prefix: str | None,
    file_key_exact: str | None,
) -> models.Filter | None:
    """Filter for LangChain / Qdrant semantic search (folder or single file)."""
    if file_key_exact:
        return models.Filter(
            must=[
                models.FieldCondition(
                    key="metadata.file_key",
                    match=models.MatchValue(value=file_key_exact),
                )
            ]
        )
    if folder_prefix and folder_prefix.strip():
        return models.Filter(
            must=[
                models.FieldCondition(
                    key="metadata.folder",
                    match=models.MatchValue(value=folder_prefix.strip()),
                )
            ]
        )
    return None


def get_langchain_retriever(
    store: QdrantVectorStore,
    *,
    k: int,
    qdrant_filter: models.Filter | None,
):
    """Expose `VectorStore.as_retriever()` for LCEL / learning (optional filter in search_kwargs)."""
    kwargs: dict = {"k": k}
    if qdrant_filter is not None:
        kwargs["filter"] = qdrant_filter
    return store.as_retriever(search_kwargs=kwargs)
