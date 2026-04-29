# Evaluation Guide

This document defines how to evaluate AI behavior in `receipt_ai` and prevent silent quality regressions.

## 1) Scope

Applies to changes in:
- `receipt_ai/features/chat/rag_service.py`
- `receipt_ai/features/extraction/retrieval/retriever.py`
- `receipt_ai/features/extraction/indexing/indexing_orchestrator.py`
- `receipt_ai/features/extraction/adapters/image_kimi_extractor.py`
- Prompt text/logic documented in `docs/PROMPTS.md`

## 2) Quality Dimensions

### A) RAG Answer Quality
- **Relevance**: answer addresses the user question directly.
- **Grounding**: answer is based on retrieved source text, not unsupported claims.
- **Completeness**: answer includes key facts present in context.

### B) Citation / Source Quality
- **Source presence**: source metadata is attached when retrieval is used.
- **Source correctness**: cited sources correspond to the answer content.
- **No fake citations**: do not claim sources that were not retrieved.

### C) Extraction Quality
- **Receipt detection**: non-receipt image should return `NOT_RECEIPT`.
- **Validation behavior**: empty or invalid extraction output must fail fast.
- **Field fidelity**: extracted content should preserve receipt text signals.

## 3) Baseline Evaluation Set

Maintain a small, deterministic baseline set for repeatable checks:

- **RAG baseline cases**
  - 5-10 representative receipt questions
  - expected answer intent
  - expected source document/file match
- **Failure-mode cases**
  - irrelevant question with weak/no context
  - sparse context query
  - stale/missing index scenario
- **Vision extraction cases**
  - valid receipt image
  - non-receipt image (`NOT_RECEIPT` expected)
  - low-quality/noisy image sample

Store fixtures under existing test assets structure and keep examples stable across runs.

## 4) Evaluation Workflow

1. **Run pre-change baseline**
   - Capture outputs for target cases before edits.
2. **Apply change**
   - Prompt/retrieval/indexing/extraction update.
3. **Run post-change baseline**
   - Compare behavior against pre-change results.
4. **Classify delta**
   - intended improvement, neutral, or regression.
5. **Record evidence in PR**
   - include changed cases and before/after summary.

## 5) Pass / Fail Policy

### Must pass (block merge if failed)
- No auth or permission bypass in AI-facing routes/features.
- No fabricated citations.
- Non-receipt path still returns `NOT_RECEIPT` for designated fixtures.
- No severe relevance regression in baseline critical questions.

### Investigate before merge
- Minor wording/style shifts with equal grounding.
- Small ranking changes with same source correctness.

### Escalate and rollback candidate
- Hallucinated factual claims not present in retrieved context.
- Sensitive data leakage risk in model output or logs.
- Broad degradation across both retrieval modes (Qdrant and JSON fallback).

## 6) PR Evidence Requirements

For any prompt/retrieval/indexing/extraction change, include:

- Affected module(s) and reason for change.
- At least one before/after example for impacted behavior.
- Confirmation that both retrieval modes were considered:
  - Qdrant enabled
  - JSON fallback path
- Test updates or rationale if test changes are not required.

## 7) Minimal PR Template Snippet

```md
## AI evaluation evidence
- Change scope: <prompt | retrieval | indexing | extraction>
- Baseline cases run: <ids/count>
- Result: <improved | neutral | regressed>
- Citation check: <pass/fail>
- Non-receipt check (`NOT_RECEIPT`): <pass/fail>
- Retrieval modes checked: <Qdrant / JSON fallback>
```

## 8) Related Docs

- `docs/PROMPTS.md`
- `docs/RAG_SETUP.md`
- `docs/RECEIPT_VALIDATION.md`
- `docs/RELEASE_CHECKLIST.md`
