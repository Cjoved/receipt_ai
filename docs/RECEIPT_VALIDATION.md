# Receipt Validation Guide

Validation logic is split into two layers:

- Prompt-level instruction (model is told to return `NOT_RECEIPT`)
- Post-response programmatic validation

## Where It Lives

- Extractor prompt: `receipt_ai/features/extraction/adapters/image_kimi_extractor.py`
- Validators: `receipt_ai/features/extraction/validators/image_receipt_validator.py`
- Config toggle: `receipt_ai/features/extraction/config.py`

## Rules

`is_likely_receipt(text)` currently checks:

- Minimum length
- Contains at least one total cue (`total`, `amount`, `subtotal`)
- Contains at least one proof cue (`date`, `time`, `invoice`, `receipt`)

If strict validation is enabled and checks fail, extraction fails.

## Config

Set in `.env`:

```env
EXTRACTION_REQUIRE_RECEIPT_SIGNALS=true
```

Use `false` to relax strict rejection (useful for experimentation).

## Why This Matters

- Prevents non-receipt images from entering RAG index.
- Improves context quality.
- Reduces hallucinations caused by irrelevant extracted text.
