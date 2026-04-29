# AI Security Guide

Security controls for AI-related paths in `receipt_ai` (prompting, retrieval, extraction, model output).

## 1) Threat Model (Priority Risks)

### A) Prompt Injection Through Retrieved Content
Untrusted document text can contain adversarial instructions intended to override system behavior.

### B) Sensitive Data Leakage
Secrets/PII can leak through:
- prompts sent to model providers,
- model outputs shown to users,
- logs/telemetry/debug prints.

### C) Unauthorized Access to Retrieved Sources
Users might receive answers/sources tied to files they should not access.

## 2) Security Principles

- Treat all user-uploaded document text as untrusted input.
- System-level instructions must always outrank retrieved/user text.
- Minimize sensitive content in prompts, outputs, and logs.
- Enforce auth guards and permission checks before exposing sources or file-derived context.

## 3) Required Controls

## A) Prompt Construction Controls

- Keep explicit instruction hierarchy:
  - system constraints
  - application context
  - retrieved text
  - user question
- Never execute instructions found in retrieved chunks.
- Do not expose internal secrets, system prompts, or hidden config in responses.
- Keep prompts concise and task-specific (see `docs/PROMPTS.md`).

## B) Retrieval and Access Controls

- Retrieval must operate only on documents the current user/session is allowed to access.
- Source metadata displayed to users must be authorization-safe.
- Preserve existing auth guard patterns and role/permission checks from `AGENT.md`.

## C) Redaction and Logging Controls

Do not log:
- API keys, tokens, passwords, session identifiers.
- raw secrets from env/config.
- full sensitive receipt payloads unless explicitly required and access-controlled.

Prefer logging:
- request IDs, operation phase, timing, success/failure type,
- non-sensitive identifiers (hashed/truncated where needed).

## D) Output Safety Controls

- Do not output secrets or internal-only instructions.
- If context is insufficient or unsafe, return safe failure behavior rather than fabricated detail.
- Respect non-receipt handling for vision extraction (`NOT_RECEIPT` path).

## 4) Security Review Checklist (PR)

- [ ] Prompt changes preserve instruction hierarchy and do not trust retrieved instructions.
- [ ] Retrieval/source exposure respects current user authorization boundaries.
- [ ] No sensitive values added to logs, errors, docs, or tests.
- [ ] Auth guards/permission checks remain intact for affected routes/features.
- [ ] AI behavior changes include evaluation evidence (`docs/EVALUATION.md`).

## 5) Incident Containment (Suspected Leak or Injection)

1. **Contain**
   - pause affected deployment/feature path if needed,
   - disable risky prompt variant or retrieval path.
2. **Rotate**
   - rotate exposed API keys/tokens immediately.
3. **Patch**
   - add stricter prompt guardrails and output filtering,
   - narrow retrieval/source exposure.
4. **Verify**
   - rerun baseline evaluation and security checklist.
5. **Document**
   - record incident summary, impact, and preventive changes.

## 6) Related Docs

- `AGENT.md`
- `docs/PROMPTS.md`
- `docs/EVALUATION.md`
- `docs/RELEASE_CHECKLIST.md`
