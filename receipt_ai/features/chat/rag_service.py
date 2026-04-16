from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate
from openai import OpenAI

from receipt_ai.features.extraction.config import ExtractionConfig
from receipt_ai.features.extraction.retrieval import ChunkRetriever, RetrievedChunk


_RAG_SYSTEM = (
    "You are Receipt AI, a helpful assistant for farmers and office users. "
    "Answer using ONLY the provided context from indexed documents when it is relevant. "
    "If the context does not contain enough information, say so clearly and avoid inventing facts. "
    "When you use information from a source, mention which source number it came from (e.g. Source 1). "
    "Keep answers concise and practical."
)

_RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", _RAG_SYSTEM),
        (
            "human",
            "Context from indexed files:\n\n{context}\n\n---\n\nUser question:\n{question}",
        ),
    ]
)


def _format_context(hits: list[RetrievedChunk]) -> str:
    blocks: list[str] = []
    for i, h in enumerate(hits, 1):
        blocks.append(
            f"[Source {i}: {h.source_name} | {h.file_key} | chunk {h.chunk_index}]\n{h.content}"
        )
    return "\n\n---\n\n".join(blocks)


def run_rag_reply(
    user_message: str,
    *,
    folder_storage_key: str | None = None,
    file_key_exact: str | None = None,
    config: ExtractionConfig | None = None,
) -> str:
    cfg = config or ExtractionConfig.from_env()
    trimmed = user_message.strip()
    if not trimmed:
        return ""

    if not cfg.kimi_api_key:
        return (
            "**Receipt AI** needs a configured API key to answer. "
            "Set `KIMI_API_KEY` in your environment and restart the app."
        )

    retriever = ChunkRetriever(cfg)
    try:
        hits = retriever.retrieve(
            trimmed,
            top_k=cfg.rag_top_k,
            folder_prefix=folder_storage_key,
            file_key_exact=file_key_exact,
        )
    except Exception as exc:
        return (
            f"Retrieval failed: {exc}\n\n"
            "If `QDRANT_URL` is set, ensure Qdrant is running and reachable. "
            "Otherwise remove `QDRANT_URL` to use the on-disk JSON index."
        )

    if not hits:
        return (
            "No indexed text was found for this question. "
            "Upload documents to an open folder and wait for indexing to finish, "
            "or open the folder that contains your files in the Files page so search is scoped to it."
        )

    context = _format_context(hits)
    prompt_messages = _RAG_PROMPT.format_messages(context=context, question=trimmed)
    openai_messages = [{"role": m.type, "content": str(m.content)} for m in prompt_messages]

    try:
        client = OpenAI(
            api_key=cfg.kimi_api_key,
            base_url=cfg.kimi_base_url,
            timeout=cfg.kimi_timeout_seconds,
        )
        result = client.chat.completions.create(
            model=cfg.kimi_chat_model,
            messages=openai_messages,
            temperature=0.25,
        )
        text = (result.choices[0].message.content or "").strip()
        return text if text else "The model returned an empty reply. Try rephrasing your question."
    except Exception as exc:
        return f"Could not get a chat reply ({exc}). Check your API key and model name (`KIMI_CHAT_MODEL`)."
