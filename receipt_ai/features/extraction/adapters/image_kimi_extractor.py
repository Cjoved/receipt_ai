from __future__ import annotations

import base64

from openai import OpenAI

from receipt_ai.features.extraction.config import ExtractionConfig
from receipt_ai.features.extraction.contracts import Extractor
from receipt_ai.features.extraction.errors import ExternalAIError
from receipt_ai.features.extraction.models import ExtractionRequest


def _guess_mime(filename: str) -> str:
    lowered = filename.lower()
    if lowered.endswith(".png"):
        return "image/png"
    if lowered.endswith(".gif"):
        return "image/gif"
    if lowered.endswith(".webp"):
        return "image/webp"
    if lowered.endswith(".bmp"):
        return "image/bmp"
    return "image/jpeg"


class ImageKimiExtractor(Extractor):
    name = "kimi-vision"

    def __init__(self, config: ExtractionConfig) -> None:
        self._config = config

    def supports(self, request: ExtractionRequest) -> bool:
        lowered = request.filename.lower()
        return lowered.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".jfif"))

    def extract(self, request: ExtractionRequest) -> str:
        if not self._config.kimi_api_key:
            raise ExternalAIError("KIMI_API_KEY is not configured.")
        try:
            client = OpenAI(
                api_key=self._config.kimi_api_key,
                base_url=self._config.kimi_base_url,
                timeout=self._config.kimi_timeout_seconds,
            )
            mime = _guess_mime(request.filename)
            b64 = base64.b64encode(request.file_bytes).decode("ascii")
            result = client.chat.completions.create(
                model=self._config.kimi_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You extract receipt text from images. Return clean plain text with key fields when found: "
                            "merchant, date, line items, tax, total, payment method."
                        ),
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"Extract the receipt text from this image: {request.filename}"},
                            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                        ],
                    },
                ],
                temperature=0.2,
            )
            text = (result.choices[0].message.content or "").strip()
            if text == "":
                raise ExternalAIError("Kimi returned empty output.")
            return text
        except ExternalAIError:
            raise
        except Exception as exc:
            raise ExternalAIError(f"Kimi extraction failed: {exc}") from exc
