from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from dataclasses import dataclass
from typing import Iterator

from langchain_core.prompts import ChatPromptTemplate
from openai import OpenAI

from receipt_ai.features.extraction.config import ExtractionConfig
from receipt_ai.features.extraction.retrieval import ChunkRetriever, RetrievedChunk

_RAG_SYSTEM = (
    "You are Receipt AI, a helpful assistant for farmers and office users. "
    "LANGUAGE: Match the user's language. If they write mainly in Filipino/Tagalog, reply entirely in "
    "Filipino/Tagalog. If mainly in English, reply in English. For mixed messages, follow the dominant "
    "language. Do not switch languages mid-answer unless the user mixes terms that require it (e.g. "
    "proper nouns). Keep citing sources as 'Source N' to match the app UI. "
    "Answer using ONLY the provided context from indexed documents when it is relevant. "
    "If the context does not contain enough information, say so clearly and avoid inventing facts. "
    "When you use information from a source, mention which source number it came from (e.g. Source 1). "
    "Source numbers are shown in relevance order from search, NOT chronological order, unless the "
    "prompt metadata explicitly says chunks were reordered for recency. "
    "Receipt OCR often misreads dates, 2-digit years, and totals. If the text is ambiguous, say so "
    "and quote the unclear fragment; prefer the clearest literal reading and avoid inventing amounts or dates. "
    "When filenames include capture timestamps (e.g. Screenshot YYYY-MM-DD HHMMSS), you may use them as a weak "
    "hint for which image is newer when the user asks for the latest/newest receipt and receipt dates conflict. "
    "Keep answers concise and practical."
)

_LATEST_RECEIPT_RE = re.compile(
    r"\b(latest|most recent|newest|last receipt|last file|newest receipt|most recent receipt|"
    r"pinakabago|pinaka-?bago|huling|pinakahuli)\b",
    re.IGNORECASE,
)

_BROAD_RECEIPTS_RE = re.compile(
    r"\b(lahat|all|every|buong|all receipts|all receipt|full list|listahan|table)\b",
    re.IGNORECASE,
)
_AMOUNT_RE = re.compile(r"(?:php|₱|p\s*)([\d][\d,]*(?:\.\d{1,2})?)", re.IGNORECASE)
_TOTAL_LINE_RE = re.compile(r"(?:total|amount due|total amount due|net amount|cash sales)\s*[:\-]?\s*(.*)", re.IGNORECASE)
_DATE_SLASH_RE = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b")
_MONTH_NAME_RE = re.compile(
    r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2}),?\s+(\d{2,4})\b",
    re.IGNORECASE,
)
_MONTH_MAP = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def _filename_recency_key(label: str) -> int:
    """Sort key from common Windows screenshot names; 0 if unknown."""
    s = label or ""
    m = re.search(r"(20\d{2})-(\d{2})-(\d{2})[^\d]?(\d{6})\b", s)
    if m:
        return int(m.group(1) + m.group(2) + m.group(3) + m.group(4))
    m2 = re.search(r"(20\d{2})-(\d{2})-(\d{2})", s)
    if m2:
        return int(m2.group(1) + m2.group(2) + m2.group(3)) * 1_000_000
    return 0


def _prepare_hits_for_prompt(user_message: str, hits: list[RetrievedChunk]) -> tuple[list[RetrievedChunk], str]:
    """Return hits possibly reordered for 'latest receipt' style questions."""
    if not hits:
        return hits, ""
    if not _LATEST_RECEIPT_RE.search(user_message):
        return list(hits), ""

    indexed = list(enumerate(hits))
    now_utc = datetime.now(UTC)

    def sort_key(item: tuple[int, RetrievedChunk]) -> tuple[int, int, int, int]:
        i, h = item
        receipt_date_ord = _latest_valid_receipt_date_ordinal(h.content, now_utc)
        epoch = h.uploaded_epoch if h.uploaded_epoch is not None else 0
        fname = _filename_recency_key(f"{h.source_name} {h.file_key}")
        return (-receipt_date_ord, -epoch, -fname, i)

    indexed.sort(key=sort_key)
    return [h for _, h in indexed], (
        "Chunks below were reordered for recency using plausible receipt dates first, then indexed_epoch / "
        "filename timestamp. Implausible future OCR dates were ignored. Source numbers were reassigned "
        "in this new order."
    )


def _normalize_year(raw_year: int) -> int:
    if raw_year < 100:
        return 2000 + raw_year
    return raw_year


def _safe_datetime(year: int, month: int, day: int) -> datetime | None:
    try:
        return datetime(year, month, day, tzinfo=UTC)
    except ValueError:
        return None


def _receipt_date_candidates(text: str) -> list[datetime]:
    out: list[datetime] = []
    src = text or ""
    for m in _DATE_SLASH_RE.finditer(src):
        month = int(m.group(1))
        day = int(m.group(2))
        year = _normalize_year(int(m.group(3)))
        dt = _safe_datetime(year, month, day)
        if dt is not None:
            out.append(dt)
    for m in _MONTH_NAME_RE.finditer(src):
        month_name = str(m.group(1)).lower()
        month = _MONTH_MAP.get(month_name)
        if month is None:
            continue
        day = int(m.group(2))
        year = _normalize_year(int(m.group(3)))
        dt = _safe_datetime(year, month, day)
        if dt is not None:
            out.append(dt)
    return out


def _latest_valid_receipt_date_ordinal(text: str, now_utc: datetime) -> int:
    candidates = _receipt_date_candidates(text)
    if not candidates:
        return 0
    upper = now_utc + timedelta(days=14)
    lower = datetime(2000, 1, 1, tzinfo=UTC)
    valid = [d for d in candidates if lower <= d <= upper]
    if not valid:
        return 0
    latest = max(valid)
    return int(latest.toordinal())

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


def _format_context(hits: list[RetrievedChunk], *, reorder_note: str = "") -> str:
    blocks: list[str] = []
    if reorder_note:
        blocks.append(f"[Retrieval note]\n{reorder_note}")
    for i, h in enumerate(hits, 1):
        meta_parts: list[str] = [f"chunk {h.chunk_index}"]
        if h.document_key and h.document_key != h.file_key:
            meta_parts.append(f"document_key={h.document_key}")
        if h.uploaded_epoch is not None:
            meta_parts.append(f"indexed_utc_epoch={h.uploaded_epoch}")
        if h.indexed_at:
            meta_parts.append(f"indexed_at={h.indexed_at}")
        head = f"[Source {i}: {h.source_name} | file_key={h.file_key} | " + " | ".join(meta_parts) + "]"
        blocks.append(f"{head}\n{h.content}")
    return "\n\n---\n\n".join(blocks)


def _is_broad_receipts_query(user_message: str) -> bool:
    text = (user_message or "").strip().lower()
    if text == "":
        return False
    if not _BROAD_RECEIPTS_RE.search(text):
        return False
    return any(k in text for k in ("receipt", "resibo", "gast", "amount", "table", "list"))


def _page_index_from_file_key(file_key: str) -> int | None:
    m = re.search(r"::p(\d+)\b", file_key or "")
    if not m:
        return None
    try:
        return int(m.group(1))
    except (TypeError, ValueError):
        return None


def _parse_amount(text: str) -> tuple[str, bool]:
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    for ln in lines:
        m = _TOTAL_LINE_RE.search(ln)
        if not m:
            continue
        found = _AMOUNT_RE.search(m.group(1))
        if found:
            val = found.group(1).replace(",", "")
            try:
                return (f"{float(val):,.2f}", False)
            except ValueError:
                continue
    # fallback: last currency-like value in text
    vals = _AMOUNT_RE.findall(text or "")
    if vals:
        raw = vals[-1].replace(",", "")
        try:
            return (f"{float(raw):,.2f}", True)
        except ValueError:
            pass
    return ("", True)


def _looks_like_noise_title(line: str) -> bool:
    l = (line or "").strip().lower()
    if l == "":
        return True
    noise = ("accreditation", "authority to print", "vat reg", "bir", "printer", "issued", "expiry")
    return any(n in l for n in noise)


def _parse_title(text: str, fallback: str) -> str:
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    for ln in lines[:12]:
        if _looks_like_noise_title(ln):
            continue
        m = re.match(r"(?:merchant|store|sold to|registered name)\s*:\s*(.+)", ln, flags=re.IGNORECASE)
        if m:
            return m.group(1).strip()
    for ln in lines[:10]:
        if _looks_like_noise_title(ln):
            continue
        if len(ln) > 3:
            return ln
    return fallback or "Unknown"


def _broad_rerank_hits(query: str, hits: list[RetrievedChunk]) -> list[RetrievedChunk]:
    q_tokens = {t for t in re.findall(r"[a-z0-9]{3,}", query.lower())}
    if not q_tokens:
        return list(hits)
    scored: list[tuple[int, int, RetrievedChunk]] = []
    for i, h in enumerate(hits):
        text = f"{h.source_name} {h.content}".lower()
        overlap = sum(1 for t in q_tokens if t in text)
        scored.append((-overlap, i, h))
    scored.sort(key=lambda x: (x[0], x[1]))
    return [h for _, _, h in scored]


def _build_broad_receipts_reply(
    hits: list[RetrievedChunk],
    mode: str,
    *,
    broad_top_k: int,
) -> RagReply:
    grouped: dict[tuple[str, int | None], list[RetrievedChunk]] = {}
    for h in hits:
        key = (h.document_key or h.file_key, _page_index_from_file_key(h.file_key))
        grouped.setdefault(key, []).append(h)

    rows: list[tuple[str, str, str, str]] = []
    ambiguous = 0
    sorted_groups = sorted(grouped.items(), key=lambda kv: ((kv[0][0] or ""), kv[0][1] or 0))
    source_hits: list[RetrievedChunk] = []
    for idx, ((doc_key, page_idx), group_hits) in enumerate(sorted_groups, start=1):
        group_hits.sort(key=lambda h: float(h.score), reverse=True)
        primary = group_hits[0]
        source_hits.append(primary)
        text = "\n".join(h.content for h in group_hits[:2])
        title = _parse_title(text, primary.source_name or doc_key or "Unknown")
        amount, fallback_amount = _parse_amount(text)
        if amount == "":
            ambiguous += 1
            amount_cell = "N/A (ambiguous OCR)"
        elif fallback_amount:
            ambiguous += 1
            amount_cell = f"Php {amount} (needs manual check)"
        else:
            amount_cell = f"Php {amount}"
        src_label = f"Source {idx}"
        if page_idx is not None:
            src_label = f"{src_label} (page {page_idx})"
        confidence = "medium" if fallback_amount or amount == "" else "high"
        rows.append((title, amount_cell, src_label, confidence))

    lines = [
        "Narito ang receipts na nakuha mula sa indexed files.",
        "",
        "| Title | Amount | Source | Confidence |",
        "| :--- | :--- | :--- | :--- |",
    ]
    for title, amount_cell, src_label, confidence in rows:
        lines.append(f"| {title} | {amount_cell} | {src_label} | {confidence} |")
    lines.extend(
        [
            "",
            (
                f"Coverage summary: requested broad mode (top_k={broad_top_k}), "
                f"{len(grouped)} page/document groups seen, {len(rows)} rows emitted, "
                f"{ambiguous} ambiguous row(s)."
            ),
            "If you need strict accounting totals, manually verify rows marked `needs manual check` or `ambiguous OCR`.",
        ]
    )
    return RagReply(content="\n".join(lines), mode=mode, sources=_build_sources(source_hits), retryable=False)


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

    broad_mode = cfg.rag_enable_broad_aggregate_mode and _is_broad_receipts_query(trimmed)

    retriever = ChunkRetriever(cfg)
    requested_top_k = cfg.rag_broad_top_k if broad_mode else cfg.rag_top_k
    try:
        hits = retriever.retrieve(
            trimmed,
            top_k=requested_top_k,
            folder_prefix=folder_storage_key,
            file_key_exact=file_key_exact,
            expand_neighbors=cfg.rag_enable_neighbor_expansion,
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

    if broad_mode:
        ordered_hits = _broad_rerank_hits(trimmed, hits) if cfg.rag_enable_broad_rerank else hits
        return _build_broad_receipts_reply(ordered_hits, mode, broad_top_k=requested_top_k)

    if not cfg.deepseek_api_key:
        msg = (
            "**Receipt AI** needs a configured DeepSeek API key to answer. "
            "Set `DEEPSEEK_API_KEY` in your environment and restart the app."
        )
        return RagReply(content=msg, mode=mode, sources=[], error=msg, retryable=False)

    hits_for_prompt, reorder_note = _prepare_hits_for_prompt(trimmed, hits)
    sources = _build_sources(hits_for_prompt)
    context = _format_context(hits_for_prompt, reorder_note=reorder_note)
    prompt_messages = _RAG_PROMPT.format_messages(context=context, question=trimmed)
    openai_messages = [{"role": _to_openai_role(m.type), "content": str(m.content)} for m in prompt_messages]
    model = cfg.deepseek_reasoning_model if mode == "reasoning" else cfg.deepseek_chat_model
    temperature = 0.1 if mode == "reasoning" else 0.15
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
