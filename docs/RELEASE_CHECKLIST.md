# Release Checklist

Use this checklist before merge/release to reduce regressions in app behavior and AI quality.

## 1) Core Engineering Checks

- [ ] Scope is limited to intended files/features.
- [ ] Tests for changed behavior are added/updated and passing.
- [ ] No secrets are committed (`.env`, keys, tokens, credentials).
- [ ] If schema changed: Alembic migration exists and is validated.
- [ ] If config changed: `.env.example` and docs are updated.

## 2) Auth and Access Checks

- [ ] Route guards still behave correctly (`login`, `protected`, `admin` paths).
- [ ] Role/permission checks still enforce privileged actions.
- [ ] User-facing auth errors are safe (no sensitive internals).

## 3) AI / RAG Checks

### A) Retrieval and Indexing
- [ ] Indexing path still completes for normal upload flow.
- [ ] Retrieval works in configured mode and returns plausible context.
- [ ] Mode parity considered:
  - [ ] Qdrant-enabled path validated.
  - [ ] JSON fallback path validated.

### B) Prompt and Generation
- [ ] Prompt changes are intentional and documented in `docs/PROMPTS.md`.
- [ ] No fabricated citation/source behavior introduced.
- [ ] Output remains grounded to retrieved context for baseline questions.

### C) Extraction Safety
- [ ] Receipt extraction still succeeds for valid sample(s).
- [ ] Non-receipt behavior (`NOT_RECEIPT`) still works for designated sample(s).
- [ ] Validation failures remain explicit and safe.

## 4) Evaluation Evidence (Required for AI Changes)

- [ ] Baseline comparison performed per `docs/EVALUATION.md`.
- [ ] Before/after examples included for impacted AI behavior.
- [ ] Any degradation is explained with mitigation or rollback note.

## 5) Observability and Runbook Readiness

- [ ] For AI behavior changes, required signals/log fields are validated per `docs/OBSERVABILITY.md`.
- [ ] High-risk changes include incident handling readiness per `docs/INCIDENT_RUNBOOK.md`.

## 6) Documentation Checks

- [ ] `docs/ARCHITECTURE.md` updated if responsibility boundaries changed.
- [ ] `docs/RAG_SETUP.md` updated if retrieval/indexing/env assumptions changed.
- [ ] `docs/SECURITY_AI.md` updated if threat controls changed.
- [ ] `docs/EVALUATION.md` updated if acceptance criteria changed.
- [ ] `docs/OBSERVABILITY.md` updated if telemetry/triage expectations changed.
- [ ] `docs/INCIDENT_RUNBOOK.md` updated if incident response policy changed.

## 7) Rollback Readiness

- [ ] Rollback path identified (feature flag/config revert/code revert plan).
- [ ] Risk notes documented (user impact, data impact, auth/security impact).
- [ ] Owner assigned for post-release monitoring.

## 8) Sign-Off Block

```md
Release/PR:
Owner:
Date:

AI surface changed: <yes/no>
High-risk areas touched:
- <auth | retrieval | prompts | extraction | migrations>

Rollback plan:
Risk notes:
Sign-off: <name/role>
```

## 9) Related Docs

- `AGENT.md`
- `docs/EVALUATION.md`
- `docs/SECURITY_AI.md`
- `docs/OBSERVABILITY.md`
- `docs/INCIDENT_RUNBOOK.md`
- `docs/PROMPTS.md`
- `docs/RAG_SETUP.md`
