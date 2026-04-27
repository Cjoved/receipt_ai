from __future__ import annotations

import json
import re
from dataclasses import replace
from pathlib import Path

from receipt_ai.features.extraction.adapters.kimi_vision_core import kimi_raw_vision_completion
from receipt_ai.features.extraction.adapters.pdf_extractor import PdfExtractor, render_pdf_pages_to_png_bytes
from receipt_ai.features.extraction.config import ExtractionConfig
from receipt_ai.features.extraction.models import ExtractionRequest


def parse_fields(text: str) -> dict[str, str]:
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    title = ""
    amount = ""
    date = ""

    for ln in lines[:20]:
        m = re.match(r"(?:merchant|store|sold to|registered name)\s*:\s*(.+)", ln, flags=re.IGNORECASE)
        if m:
            title = m.group(1).strip()
            break
    if not title:
        for ln in lines[:8]:
            low = ln.lower()
            if len(ln) > 3 and not any(x in low for x in ("vat", "tin", "bir", "printer", "authority")):
                title = ln
                break

    for ln in lines:
        if re.search(r"date\s*[:\-]", ln, flags=re.IGNORECASE):
            date = ln
            break
    if not date:
        m = re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", text or "")
        if m:
            date = m.group(0)

    vals = re.findall(r"(?:php|₱|p\s*)([\d][\d,]*(?:\.\d{1,2})?)", text or "", flags=re.IGNORECASE)
    if vals:
        amount = vals[-1]
    return {"title": title, "date": date, "amount": amount}


def summarize_pages(merged_text: str) -> list[dict]:
    pages: list[dict] = []
    chunks = re.split(r"(?m)^---\s*Page\s+(\d+)\s*---\s*$", merged_text or "")
    if len(chunks) <= 1:
        return pages
    for i in range(1, len(chunks), 2):
        page_no = int(chunks[i])
        body = chunks[i + 1].strip() if i + 1 < len(chunks) else ""
        fields = parse_fields(body)
        skipped = body.startswith("[Extraction skipped:")
        skip_reason = ""
        if skipped:
            skip_reason = body.replace("[Extraction skipped:", "").replace("]", "").strip()
        pages.append(
            {
                "page": page_no,
                "skipped": skipped,
                "skip_reason": skip_reason,
                "preview": body[:220],
                **fields,
            }
        )
    return pages


def main() -> None:
    pdf_path = Path(r"c:\Users\Crich Joved\Downloads\budget first week ltc.pdf")
    out_path = Path(r"c:\Users\Crich Joved\OneDrive\Desktop\receipt_ai\assets\extracted_text\compare_budget_ltc_extraction.json")
    if not pdf_path.exists():
        raise SystemExit(f"PDF not found: {pdf_path}")

    file_bytes = pdf_path.read_bytes()
    base_cfg = ExtractionConfig.from_env()
    if not base_cfg.kimi_api_key:
        raise SystemExit("KIMI_API_KEY is not configured in environment/.env")
    cfg = replace(base_cfg, pdf_extraction_mode="vision")
    req = ExtractionRequest(
        filename=pdf_path.name,
        content_type="application/pdf",
        file_bytes=file_bytes,
        storage_folder="manual_compare",
    )

    extractor = PdfExtractor(cfg)
    pipeline_text = extractor.extract(req)
    pipeline_stats = extractor.last_vision_stats
    page_pngs = render_pdf_pages_to_png_bytes(file_bytes, cfg.pdf_max_pages, cfg.pdf_render_dpi)

    new_mode_pages: list[dict] = []
    old_mode_pages: list[dict] = []
    for i, png in enumerate(page_pngs, start=1):
        label = f"{pdf_path.name} (page {i})"
        new_text = kimi_raw_vision_completion(cfg, image_bytes=png, mime="image/png", prompt_label=label, pdf_page_mode=True)
        old_text = kimi_raw_vision_completion(cfg, image_bytes=png, mime="image/png", prompt_label=label, pdf_page_mode=False)
        new_mode_pages.append(
            {
                "page": i,
                "not_receipt": (new_text.strip() == "NOT_RECEIPT"),
                "preview": new_text[:220],
                **parse_fields(new_text),
            }
        )
        old_mode_pages.append(
            {
                "page": i,
                "not_receipt": (old_text.strip() == "NOT_RECEIPT"),
                "preview": old_text[:220],
                **parse_fields(old_text),
            }
        )

    comparison = {
        "pdf": str(pdf_path),
        "config": {
            "pdf_render_dpi": cfg.pdf_render_dpi,
            "pdf_retry_pages": cfg.pdf_retry_pages,
            "pdf_retry_dpi_step": cfg.pdf_retry_dpi_step,
            "kimi_model": cfg.kimi_model,
        },
        "pipeline": {
            "extractor": extractor.name,
            "stats": pipeline_stats,
            "pages": summarize_pages(pipeline_text),
        },
        "direct_kimi_pdf_page_mode": {
            "pages_total": len(new_mode_pages),
            "not_receipt_count": sum(1 for p in new_mode_pages if p["not_receipt"]),
            "pages": new_mode_pages,
        },
        "direct_kimi_receipt_only_mode": {
            "pages_total": len(old_mode_pages),
            "not_receipt_count": sum(1 for p in old_mode_pages if p["not_receipt"]),
            "pages": old_mode_pages,
        },
    }
    out_path.write_text(json.dumps(comparison, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        json.dumps(
            {
                "output_json": str(out_path),
                "pipeline_pages": len(comparison["pipeline"]["pages"]),
                "pipeline_skipped": comparison["pipeline"]["stats"].get("pages_skipped", 0),
                "new_mode_not_receipt": comparison["direct_kimi_pdf_page_mode"]["not_receipt_count"],
                "old_mode_not_receipt": comparison["direct_kimi_receipt_only_mode"]["not_receipt_count"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
