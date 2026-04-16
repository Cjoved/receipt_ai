# RAG Setup Guide

This project supports two retrieval modes:

- JSON index fallback (local file scan)
- Qdrant vector DB (recommended for learning vector DB workflows)

## Required Env Vars

Add these in `.env`:

```env
KIMI_API_KEY=your_key
KIMI_BASE_URL=https://api.moonshot.ai/v1
KIMI_CHAT_MODEL=moonshot-v1-8k
KIMI_VISION_MODEL=moonshot-v1-8k-vision-preview
FASTEMBED_MODEL=BAAI/bge-small-en-v1.5
RAG_TOP_K=8

QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=receipt_chunks
# optional:
# QDRANT_API_KEY=...
```

## Run Qdrant

```bash
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant
```

## How Indexing Works

File: `receipt_ai/features/extraction/indexing/indexing_orchestrator.py`

1. Extracted text is normalized and chunked.
2. Chunks are embedded via FastEmbed.
3. Chunks are always saved to JSON (`assets/chunk_index` by default).
4. If `QDRANT_URL` is set, chunks are also upserted to Qdrant.

Qdrant helper module:

- `receipt_ai/features/extraction/indexing/qdrant_index.py`

## How Retrieval Works

File: `receipt_ai/features/extraction/retrieval/retriever.py`

- If Qdrant is enabled: LangChain `QdrantVectorStore.similarity_search_with_score(...)`
- Else: JSON chunks + cosine similarity in Python

## App Run

```bash
uv run reflex run
```

Then:

1. Upload file(s) in Files page.
2. Wait for indexing to complete.
3. Ask questions in Chat page.
