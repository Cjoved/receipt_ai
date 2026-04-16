from __future__ import annotations

import asyncio

from receipt_ai.features.extraction.indexing import IndexingOrchestrator, IndexingRequest


async def process_uploaded_document(payload: IndexingRequest) -> str:
    orchestrator = IndexingOrchestrator()
    return await asyncio.to_thread(orchestrator.process, payload)


def enqueue_uploaded_document(payload: IndexingRequest) -> asyncio.Task:
    return asyncio.create_task(process_uploaded_document(payload))
