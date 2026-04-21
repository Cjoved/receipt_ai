from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

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


def _to_openai_role(message_type: str) -> str:
    t = (message_type or "").strip().lower()
    if t == "human":
        return "user"
    if t == "ai":
        return "assistant"
    if t in {"system", "user", "assistant", "tool"}:
        return t
    return "user"


@dataclass(frozen=True)
class RagSource:
    source_index: int
    file_key: str
    source_name: str
    chunk_index: int
    score: float


@dataclass(frozen=True)
class RagReply:
    content: str
    mode: str
    sources: list[RagSource]
    error: str = ""
    retryable: bool = False


@dataclass(frozen=True)
class _RagReady:
    """Successful retrieval + prompt; ready for chat completion (stream or not)."""

    cfg: ExtractionConfig
    openai_messages: list[dict[str, str]]
    model: str
    temperature: float
    sources: list[RagSource]
    mode: str


def _format_context(hits: list[RetrievedChunk]) -> str:
    blocks: list[str] = []
    for i, h in enumerate(hits, 1):
        blocks.append(
            f"[Source {i}: {h.source_name} | {h.file_key} | chunk {h.chunk_index}]\n{h.content}"
        )
    return "\n\n---\n\n".join(blocks)


def _build_sources(hits: list[RetrievedChunk]) -> list[RagSource]:
    return [
        RagSource(
            source_index=i,
            file_key=h.file_key,
            source_name=h.source_name,
            chunk_index=h.chunk_index,
            score=float(h.score),
        )
        for i, h in enumerate(hits, 1)
    ]


def _rag_setup(
    user_message: str,
    *,
    folder_storage_key: str | None = None,
    file_key_exact: str | None = None,
    chat_mode: str = "normal",
    config: ExtractionConfig | None = None,
) -> RagReply | _RagReady:
    cfg = config or ExtractionConfig.from_env()
    trimmed = user_message.strip()
    mode = (chat_mode or "normal").strip().lower()
    if mode not in {"normal", "reasoning"}:
        mode = "normal"
    if not trimmed:
        return RagReply(content="", mode=mode, sources=[], retryable=False)

    if not cfg.deepseek_api_key:
        msg = (
            "**Receipt AI** needs a configured DeepSeek API key to answer. "
            "Set `DEEPSEEK_API_KEY` in your environment and restart the app."
        )
        return RagReply(content=msg, mode=mode, sources=[], error=msg, retryable=False)

    retriever = ChunkRetriever(cfg)
    try:
        hits = retriever.retrieve(
            trimmed,
            top_k=cfg.rag_top_k,
            folder_prefix=folder_storage_key,
            file_key_exact=file_key_exact,
        )
    except Exception as exc:
        msg = (
            f"Retrieval failed: {exc}\n\n"
            "If `QDRANT_URL` is set, ensure Qdrant is running and reachable. "
            "Otherwise remove `QDRANT_URL` to use the on-disk JSON index."
        )
        return RagReply(content=msg, mode=mode, sources=[], error=str(exc), retryable=True)

    if not hits:
        msg = (
            "No indexed text was found for this question. "
            "Upload documents to an open folder and wait for indexing to finish, "
            "or open the folder that contains your files in the Files page so search is scoped to it."
        )
        return RagReply(content=msg, mode=mode, sources=[], retryable=False)

    sources = _build_sources(hits)
    context = _format_context(hits)
    prompt_messages = _RAG_PROMPT.format_messages(context=context, question=trimmed)
    openai_messages = [{"role": _to_openai_role(m.type), "content": str(m.content)} for m in prompt_messages]
    model = cfg.deepseek_reasoning_model if mode == "reasoning" else cfg.deepseek_chat_model
    temperature = 0.1 if mode == "reasoning" else 0.25
    return _RagReady(
        cfg=cfg,
        openai_messages=openai_messages,
        model=model,
        temperature=temperature,
        sources=sources,
        mode=mode,
    )


def run_rag_reply(
    user_message: str,
    *,
    folder_storage_key: str | None = None,
    file_key_exact: str | None = None,
    chat_mode: str = "normal",
    config: ExtractionConfig | None = None,
) -> RagReply:
    setup = _rag_setup(
        user_message,
        folder_storage_key=folder_storage_key,
        file_key_exact=file_key_exact,
        chat_mode=chat_mode,
        config=config,
    )
    if isinstance(setup, RagReply):
        return setup

    try:
        client = OpenAI(
            api_key=setup.cfg.deepseek_api_key,
            base_url=setup.cfg.deepseek_base_url,
            timeout=setup.cfg.deepseek_timeout_seconds,
        )
        result = client.chat.completions.create(
            model=setup.model,
            messages=setup.openai_messages,
            temperature=setup.temperature,
        )
        text = (result.choices[0].message.content or "").strip()
        if not text:
            text = "The model returned an empty reply. Try rephrasing your question."
        return RagReply(content=text, mode=setup.mode, sources=setup.sources, retryable=False)
    except Exception as exc:
        msg = (
            f"Could not get a chat reply in `{setup.mode}` mode ({exc}). "
            "Check `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, and model names "
            "(`DEEPSEEK_CHAT_MODEL` / `DEEPSEEK_REASONING_MODEL`)."
        )
        return RagReply(
            content=msg,
            mode=setup.mode,
            sources=setup.sources,
            error=str(exc),
            retryable=True,
        )


def stream_rag_chunks(
    user_message: str,
    *,
    folder_storage_key: str | None = None,
    file_key_exact: str | None = None,
    chat_mode: str = "normal",
    config: ExtractionConfig | None = None,
) -> Iterator[str]:
    """Yield text deltas from the chat completion stream.

    On success the generator's return value (``StopIteration.value``) is the final
    :class:`RagReply`. On setup failure (no key, no hits, retrieval error) the
    generator returns a :class:`RagReply` without yielding any chunk.
    """
    setup = _rag_setup(
        user_message,
        folder_storage_key=folder_storage_key,
        file_key_exact=file_key_exact,
        chat_mode=chat_mode,
        config=config,
    )
    if isinstance(setup, RagReply):
        return setup

    try:
        client = OpenAI(
            api_key=setup.cfg.deepseek_api_key,
            base_url=setup.cfg.deepseek_base_url,
            timeout=setup.cfg.deepseek_timeout_seconds,
        )
        stream = client.chat.completions.create(
            model=setup.model,
            messages=setup.openai_messages,
            temperature=setup.temperature,
            stream=True,
        )
        parts: list[str] = []
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta is None:
                continue
            content = getattr(delta, "content", None) or ""
            if content:
                parts.append(content)
                yield content
        text = "".join(parts).strip()
        if not text:
            text = "The model returned an empty reply. Try rephrasing your question."
        return RagReply(content=text, mode=setup.mode, sources=setup.sources, retryable=False)
    except Exception as exc:
        msg = (
            f"Could not get a chat reply in `{setup.mode}` mode ({exc}). "
            "Check `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, and model names "
            "(`DEEPSEEK_CHAT_MODEL` / `DEEPSEEK_REASONING_MODEL`)."
        )
        return RagReply(
            content=msg,
            mode=setup.mode,
            sources=setup.sources,
            error=str(exc),
            retryable=True,
        )


def stream_iter_next(gen: Iterator[str]) -> tuple[str, str | RagReply]:
    """Advance a streaming generator in a worker thread; returns ``("chunk", s)`` or ``("done", reply)``."""
    try:
        return ("chunk", next(gen))
    except StopIteration as e:
        val = e.value
        if isinstance(val, RagReply):
            return ("done", val)
        return ("done", RagReply(content="", mode="normal", sources=[], error="Stream ended unexpectedly.", retryable=False))
