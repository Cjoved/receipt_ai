# Observability Guide

Operational visibility standards for AI flows in `receipt_ai`.

## 1) Scope

Use this guide for changes affecting:
- `receipt_ai/features/extraction/adapters/*`
- `receipt_ai/features/extraction/indexing/*`
- `receipt_ai/features/extraction/retrieval/retriever.py`
- `receipt_ai/features/chat/rag_service.py`
- `receipt_ai/features/chat/service.py`

## 2) Pipeline Stages to Observe

Track AI behavior across these stages:
1. Extraction
2. Indexing
3. Retrieval
4. Prompt assembly
5. Generation/response

A debugging session should identify which stage first diverges from expected behavior.

## 3) Minimum Telemetry Fields

For each AI request path, include structured, non-sensitive telemetry where possible:

- `request_id` or correlation ID
- `user_id` (non-sensitive identifier format)
- `route` / feature context (`chat`, `files`, etc.)
- `pipeline_stage`
- `retrieval_mode` (`qdrant` or `json_fallback`)
- `top_k` used and retrieved hit count
- score summary (min/max/avg) without raw sensitive text dumps
- model/provider name
- latency per stage + total latency
- retry count and error category (timeout, validation, auth, provider, etc.)

## 4) Do-Not-Log Policy

Never log:
- API keys, tokens, passwords, session secrets
- full prompt text containing sensitive document content
- raw full extracted receipt payloads unless explicitly access-controlled
- hidden/system instructions intended to remain internal

Align with `docs/SECURITY_AI.md` for redaction and leakage prevention.

## 5) Stage-Level Health Signals

### A) Extraction
- success/failure counts by extractor type
- validation rejection counts (`NOT_RECEIPT`, empty output, failed receipt signals)
- average extraction latency

### B) Indexing
- chunks produced per file
- embedding success/failure
- JSON persistence result
- Qdrant upsert result (when enabled)

### C) Retrieval
- retrieval mode used
- number of hits returned
- score distribution summary
- zero-hit rate trend

### D) Prompt + Generation
- prompt assembly success/failure
- provider call latency and failures
- response generation success/failure
- citation/source attachment presence

## 6) Debug Playbooks

## Playbook A: “Bad Answer” Investigation

1. Confirm request context (question, route, user permissions).
2. Check retrieval mode and hit quality:
   - zero/weak hits -> retrieval/index problem likely.
3. Verify prompt assembly path:
   - context insertion and question formatting.
4. Verify provider outcome:
   - timeout/rate limit/model failure vs semantic quality issue.
5. Validate citation/source attachment:
   - if answer claims facts without valid sources, treat as high priority.

## Playbook B: “Indexing Not Reflected in Chat”

1. Confirm upload and extraction success.
2. Confirm chunk generation and persistence.
3. Confirm Qdrant upsert result (if enabled) or JSON index update.
4. Confirm retrieval mode at query time matches indexed backend.
5. Re-run with same query and inspect hit count/score trend.

## 7) Initial Baseline Expectations

Use qualitative baselines first; tighten to numeric SLOs later:
- AI responses should complete without repeated timeouts in normal local/dev runs.
- Retrieval should return non-zero relevant hits for known-indexed sample questions.
- Citation metadata should be present for retrieval-backed answers.
- Non-receipt and invalid extraction paths should fail explicitly, not silently.

## 8) Integration with Existing Docs

- Evaluation policy: `docs/EVALUATION.md`
- Security controls: `docs/SECURITY_AI.md`
- Release gate checks: `docs/RELEASE_CHECKLIST.md`
- Prompt ownership: `docs/PROMPTS.md`
- Retrieval/index setup: `docs/RAG_SETUP.md`
