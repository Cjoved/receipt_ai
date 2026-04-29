# AGENT.md

Project operating guide for AI agents working in `receipt_ai`.

## 1) Mission and Scope

- Build and maintain `receipt_ai` as a modular monolith.
- Prefer incremental, feature-bounded changes over large cross-cutting rewrites.
- Keep behavior explicit and test-backed, especially for auth, extraction, and retrieval.

## 2) Stack Snapshot

- Backend/UI framework: Reflex (`receipt_ai` package).
- Language/runtime: Python `>=3.12`.
- Dependency/runtime manager: `uv`.
- Database: PostgreSQL via async SQLAlchemy + Alembic migrations.
- Storage: S3-compatible Wasabi.
- Retrieval/indexing: Qdrant when configured, JSON fallback supported.

## 3) Architecture Boundaries

- `receipt_ai/pages/`: route pages and UI wiring.
- `receipt_ai/components/`: reusable UI components.
- `receipt_ai/features/<feature>/`: feature logic and service orchestration.
- `receipt_ai/core/db/`: models, DB config, and async session plumbing.
- `alembic/versions/`: schema migrations.
- `tests/`: unit/service/state and route behavior tests.

Rules:

- Put business logic and I/O in feature service modules, not in page files.
- Keep state classes focused on orchestration and UI flow.
- Keep route registration centralized in `receipt_ai/app.py`.

## 4) Local Development Commands

- Install/sync deps: `uv sync`
- Run app: `uv run reflex run`
- Apply migrations: `alembic upgrade head`
- Run tests: `uv run pytest`

If a schema/model change is introduced, include the Alembic migration in the same change set.

Frontend prerequisites matter in this repo (Reflex generates `.web/` and installs npm deps on first successful run):
- Prefer **Python `>=3.12`**, **Node `>=20.19`**, and **`uv`** (see root `README.md` for version checks).
- `.web/` is generated output: do not treat it as the source of truth for UI changes.

## 5) Frontend (Reflex) Debugging Playbook

Goal: reduce “it works on my machine” UI regressions by checking the usual failure modes in a consistent order.

- **Interpreter + deps**: confirm the IDE/runtime is using `.venv` (Windows: `.venv\\Scripts\\python.exe`) per `README.md`. Wrong interpreter causes confusing import/type issues.
- **Node/npm health**: verify `node -v` meets Reflex expectations; npm registry/DNS failures are common — see Troubleshooting in `README.md`.
- **Rebuild signals**: Reflex emits rebuild errors in the terminal — read them before guessing in Python.
- **State correctness**:
  - UI should bind to `rx.State` fields and events intentionally; avoid burying UX logic in unrelated pages.
  - Prefer explicit redirects/guards/toast patterns consistent with existing `AuthState` patterns rather than inventing one-off routing.
- **OneDrive path caveat**: syncing can slow installs and amplify flaky npm/tooling behavior; if you hit weird install slowness, consider the guidance in `README.md`.

Verification order (fast checks):
1. Restart `uv run reflex run`
2. Hard refresh the browser on the tested route
3. Re-check bindings (component props vs State fields/events)
4. If still wrong, isolate with a minimal component render (don’t refactor broadly)

Deep UI styling guidance is optional tooling: `.cursor/skills/frontend-design/SKILL.md` (prefer existing theme/tokens first).

## 6) Prompt + RAG Engineering Playbook

Goal: separate “LLM looks wrong” bugs from retrieval/indexing/configuration bugs.

Canonical references:
- Retrieval modes + indexing/retrieval entrypoints: `docs/RAG_SETUP.md`
- Prompt ownership + versioning expectations: `docs/PROMPTS.md`
- Retrieval implementation: `receipt_ai/features/extraction/retrieval/retriever.py`
- RAG prompting + assembly: `receipt_ai/features/chat/rag_service.py`

Invariants agents should respect:
- **Two retrieval modes exist** (JSON index fallback vs Qdrant). Behavior can differ materially when `QDRANT_URL` toggles.
- Indexing persists JSON chunks and optionally upserts into Qdrant — confirm “indexed” status before diagnosing chat answers.
- **Prompt edits are behavioral changes**. Keep constraints explicit and short (`docs/PROMPTS.md`). If output quality shifts materially, prefer adding/adjusting tests or a small deterministic fixture over endless prompt churn.

Debugging checklist:
1. **Is retrieval returning relevant chunks?** (scores empty / wrong corpus / stale index vs UI bug).
2. **Is the model receiving the assembled prompt you think?** (template variables/context ordering in `rag_service.py`, not vibes).
3. **Are env knobs consistent locally?** (keys/base URLs/top-k/collection naming — see `.env.example` + `docs/RAG_SETUP.md`).
4. **Are extraction/indexing prerequisites satisfied before chat?** (upload → indexing completion path).

## 7) Coding Conventions

- Add type hints to new/updated public functions.
- Prefer small, composable service functions over large state methods.
- Preserve existing naming style (`*_service.py`, `config.py`, `types.py`, `state_actions_*.py`).
- Avoid leaking infra concerns into UI/page modules.

## 8) Security and Auth Guardrails

- Do not bypass route guards (`guard_login_route`, `guard_protected_route`, `guard_admin_route`).
- Keep token security patterns intact: hashed tokens, expiry, one-time consumption where applicable.
- Preserve user-safe auth error messages (no sensitive internals in UI-facing text).
- Any privileged action must enforce explicit role/permission checks.

## 9) Data and External Service Guardrails

- Preserve retrieval behavior across both modes:
  - Qdrant-enabled path (when configured).
  - Local/JSON fallback path (when vector DB is unavailable).
- Keep storage/index interactions idempotent-friendly and retry-safe where practical.
- Do not hardcode secrets, endpoints, or credentials.

## 10) Testing Expectations

- Every behavior change should add/update tests in `tests/`.
- Auth-related changes must include:
  - success-path coverage,
  - failure/guard-path coverage,
  - regression checks for security-sensitive flows.
- Extraction/retrieval changes should cover success and degraded/error scenarios.

## 11) Config and Secrets

- Never commit real secrets or environment files.
- When adding config, update:
  - `.env.example`
  - relevant docs under `docs/`
- Keep defaults safe and explicit.

## 12) Documentation Hygiene

- Update `docs/ARCHITECTURE.md` when feature boundaries or core flow ownership changes.
- Keep docs aligned with run/test/migration commands.
- For AI-related changes, consult and update when needed:
  - `docs/EVALUATION.md`
  - `docs/SECURITY_AI.md`
  - `docs/RELEASE_CHECKLIST.md`
  - `docs/OBSERVABILITY.md`
  - `docs/INCIDENT_RUNBOOK.md`
- Prefer concise docs that explain responsibilities and invariants, not only implementation detail.

## 13) Change Checklist (Before Handoff)

- Code stays within intended architecture boundaries.
- Tests added/updated and passing locally.
- Migrations included (if schema changed).
- `.env.example` and docs updated (if config changed).
- No secrets committed.

Prompting templates moved to `docs/CHAT_TEMPLATES.md` to keep this file policy-focused.

