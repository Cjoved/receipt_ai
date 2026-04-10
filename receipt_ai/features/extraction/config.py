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
    kimi_timeout_seconds: int = 60

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
            kimi_timeout_seconds=_env_int("KIMI_TIMEOUT_SECONDS", 60),
        )
