from __future__ import annotations

from dataclasses import dataclass
import os

from dotenv import load_dotenv


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if raw == "":
        return default
    return raw in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_optional_int(name: str, default: int | None = None) -> int | None:
    raw = os.getenv(name, "").strip().lower()
    if raw in {"", "none", "null", "off", "0"}:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_pdf_extraction_mode() -> str:
    raw = os.getenv("PDF_EXTRACTION_MODE", "auto").strip().lower()
    if raw in {"auto", "text", "vision"}:
        return raw
    return "auto"


@dataclass(frozen=True)
class ExtractionConfig:
    enable_on_upload: bool = True
    enable_txt_output: bool = True
    output_dir: str = "assets/extracted_text"
    max_extract_bytes: int = 15_000_000
    max_sheet_rows: int = 500
    max_sheet_cols: int = 64
    kimi_api_key: str = ""
    kimi_base_url: str = "https://api.moonshot.ai/v1"
    kimi_model: str = "moonshot-v1-8k-vision-preview"
    kimi_timeout_seconds: int | None = None
    require_receipt_signals: bool = True
    chunk_size: int = 1200
    chunk_overlap: int = 180
    chunk_min_chars: int = 40
    embedding_batch_size: int = 64
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_max_retries: int = 2
    indexing_processing_stale_seconds: int = 900
    index_output_dir: str = "assets/chunk_index"
    kimi_chat_model: str = "moonshot-v1-8k"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_chat_model: str = "deepseek-chat"
    deepseek_reasoning_model: str = "deepseek-reasoner"
    deepseek_timeout_seconds: int = 60
    rag_top_k: int = 8
    rag_broad_top_k: int = 40
    rag_enable_broad_aggregate_mode: bool = False
    rag_enable_neighbor_expansion: bool = False
    rag_enable_broad_rerank: bool = False
    # Required: indexing must upsert to Qdrant.
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection: str = "receipt_chunks"
    # PDF: auto tries pypdf text first; falls back to per-page Kimi vision when text is short.
    pdf_extraction_mode: str = "auto"
    pdf_auto_min_text_chars: int = 120
    pdf_render_dpi: int = 260
    pdf_max_pages: int = 40
    pdf_retry_pages: int = 1
    pdf_retry_dpi_step: int = 40

    @classmethod
    def from_env(cls) -> "ExtractionConfig":
        load_dotenv()
        return cls(
            enable_on_upload=_env_bool("EXTRACTION_ENABLE_ON_UPLOAD", True),
            enable_txt_output=_env_bool("EXTRACTION_ENABLE_TXT_OUTPUT", True),
            output_dir=os.getenv("EXTRACTION_OUTPUT_DIR", "assets/extracted_text").strip() or "assets/extracted_text",
            max_extract_bytes=_env_int("EXTRACTION_MAX_BYTES", 15_000_000),
            max_sheet_rows=_env_int("EXTRACTION_MAX_SHEET_ROWS", 500),
            max_sheet_cols=_env_int("EXTRACTION_MAX_SHEET_COLS", 64),
            kimi_api_key=os.getenv("KIMI_API_KEY", "").strip(),
            kimi_base_url=os.getenv("KIMI_BASE_URL", "https://api.moonshot.ai/v1").strip() or "https://api.moonshot.ai/v1",
            kimi_model=os.getenv("KIMI_VISION_MODEL", "moonshot-v1-8k-vision-preview").strip()
            or "moonshot-v1-8k-vision-preview",
            kimi_timeout_seconds=_env_optional_int("KIMI_TIMEOUT_SECONDS", None),
            require_receipt_signals=_env_bool("EXTRACTION_REQUIRE_RECEIPT_SIGNALS", True),
            chunk_size=_env_int("CHUNK_SIZE", 1200),
            chunk_overlap=_env_int("CHUNK_OVERLAP", 180),
            chunk_min_chars=_env_int("CHUNK_MIN_CHARS", 40),
            embedding_batch_size=_env_int("EMBEDDING_BATCH_SIZE", 64),
            embedding_model=os.getenv("FASTEMBED_MODEL", "BAAI/bge-small-en-v1.5").strip() or "BAAI/bge-small-en-v1.5",
            embedding_max_retries=_env_int("EMBEDDING_MAX_RETRIES", 2),
            indexing_processing_stale_seconds=max(30, _env_int("INDEXING_PROCESSING_STALE_SECONDS", 900)),
            index_output_dir=os.getenv("INDEX_OUTPUT_DIR", "assets/chunk_index").strip() or "assets/chunk_index",
            kimi_chat_model=os.getenv("KIMI_CHAT_MODEL", "moonshot-v1-8k").strip() or "moonshot-v1-8k",
            deepseek_api_key=(os.getenv("DEEPSEEK_API_KEY", "").strip() or os.getenv("KIMI_API_KEY", "").strip()),
            deepseek_base_url=(
                os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip() or "https://api.deepseek.com"
            ),
            deepseek_chat_model=os.getenv("DEEPSEEK_CHAT_MODEL", "deepseek-chat").strip() or "deepseek-chat",
            deepseek_reasoning_model=(
                os.getenv("DEEPSEEK_REASONING_MODEL", "deepseek-reasoner").strip() or "deepseek-reasoner"
            ),
            deepseek_timeout_seconds=_env_int("DEEPSEEK_TIMEOUT_SECONDS", _env_int("KIMI_TIMEOUT_SECONDS", 30)),
            rag_top_k=_env_int("RAG_TOP_K", 8),
            rag_broad_top_k=max(8, _env_int("RAG_BROAD_TOP_K", 40)),
            rag_enable_broad_aggregate_mode=_env_bool("RAG_ENABLE_BROAD_AGGREGATE_MODE", False),
            rag_enable_neighbor_expansion=_env_bool("RAG_ENABLE_NEIGHBOR_EXPANSION", False),
            rag_enable_broad_rerank=_env_bool("RAG_ENABLE_BROAD_RERANK", False),
            qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333").strip() or "http://localhost:6333",
            qdrant_api_key=os.getenv("QDRANT_API_KEY", "").strip(),
            qdrant_collection=os.getenv("QDRANT_COLLECTION", "receipt_chunks").strip() or "receipt_chunks",
            pdf_extraction_mode=_env_pdf_extraction_mode(),
            pdf_auto_min_text_chars=_env_int("PDF_AUTO_MIN_TEXT_CHARS", 120),
            pdf_render_dpi=max(72, _env_int("PDF_RENDER_DPI", 260)),
            pdf_max_pages=max(1, _env_int("PDF_MAX_PAGES", 40)),
            pdf_retry_pages=max(0, _env_int("PDF_RETRY_PAGES", 1)),
            pdf_retry_dpi_step=max(10, _env_int("PDF_RETRY_DPI_STEP", 40)),
        )
