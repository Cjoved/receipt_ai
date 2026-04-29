# Chat Templates

Practical prompt templates for Cursor chat/composer in this repo.

Always pair these with `@AGENT.md` and relevant file references (`@path/to/file.py`) for best results.
Your `.cursor/rules/*.mdc` are always-on guardrails, but explicitly naming docs in prompts improves output quality.

## 1) Safe Default (Any Task)

```md
Task: <one clear outcome>

Context:
- Follow `AGENT.md` constraints.
- Relevant files: <@file1>, <@file2>
- Scope limit: <in scope / out of scope>

Requirements:
- Keep architecture boundaries (`pages/components/features/core/db`) intact.
- Do not change unrelated files.
- Add/update tests for changed behavior.

Verification:
- Run: `uv run pytest` (or targeted tests)
- If schema changed: include Alembic migration.

Deliverable:
- Implement changes directly.
- Return: what changed, tests run, and risks/next steps.
```

## 2) Frontend / Reflex Bugfix

```md
Fix this UI issue: <bug summary>

Repro:
1) <step 1>
2) <step 2>
3) <actual vs expected>

Constraints:
- Follow `AGENT.md` Frontend Debugging Playbook.
- Keep changes in source files (`pages/`, `components/`, `features/*/state*`), not `.web/`.
- Respect existing state bindings and route guards.

Inspect first:
- <@receipt_ai/pages/...>
- <@receipt_ai/components/...>
- <@receipt_ai/features/.../state.py>

Verification:
- Confirm route-level behavior.
- Add/adjust tests if behavior changed.
```

## 3) Prompt + RAG Debug

```md
Investigate RAG quality issue: <short problem>

Symptoms:
- Question: "<user query example>"
- Bad output: "<observed behavior>"
- Expected: "<expected behavior>"

Constraints:
- Follow `AGENT.md` Prompt + RAG Engineering Playbook.
- Split diagnosis into: retrieval vs prompt assembly vs config/env.
- Avoid blind prompt churn.

Check first:
- `receipt_ai/features/extraction/retrieval/retriever.py`
- `receipt_ai/features/chat/rag_service.py`
- `docs/RAG_SETUP.md`, `docs/PROMPTS.md`

Deliverable:
- Root cause: (retrieval | prompt | env/config | mixed)
- Minimal fix (code/doc/config)
- Regression test or deterministic fixture update
```

## 4) New Feature (Low Regression)

```md
Build feature: <feature name>

Business goal:
- <why this feature exists>

Scope:
- In: <exact behaviors>
- Out: <explicit non-goals>

Architecture constraints:
- UI composition in `pages/components`
- Orchestration in `State`
- Business logic/I-O in `features/<feature>/*_service.py`

Quality bar:
- Type hints for new public functions
- Tests for success + failure/guard paths
- Update docs if behavior/config changes
```

## 5) Code Review Request

```md
Review these changes against `AGENT.md`:
- Focus: bugs, regressions, security/auth risks, missing tests.
- Output format:
  1) Findings by severity
  2) Open questions/assumptions
  3) Short change summary
```

## 6) Anti-Patterns (Avoid)

- “Fix this quickly” with no repro and no expected result.
- Frontend bug requests without route/state file context.
- Multiple unrelated asks in one prompt.
- “Improve RAG” without failing examples.
- “Large refactor” plus “minimal change” in the same request.

## 7) Quick Pre-Send Checklist

- Is the outcome explicit in one sentence?
- Did I attach key files with `@...`?
- Did I set in-scope and out-of-scope?
- Did I define expected behavior and verification?
- Did I require tests (or explain why not)?

## 8) Use Cases for New Docs and Rules

Use these prompts when you want the assistant to follow the new AI ops documentation and Cursor rules intentionally.

### A) AI Change With Evaluation + Release Evidence

```md
Implement this AI-related change: <short change>

Follow:
- `@AGENT.md`
- `@docs/EVALUATION.md`
- `@docs/RELEASE_CHECKLIST.md`
- `@docs/OBSERVABILITY.md`
- `@docs/SECURITY_AI.md`

Constraints:
- Keep architecture boundaries intact.
- Include evaluation evidence and release checklist impact.
- Add/update docs if behavior/policy changed.

Deliverable:
- Code/doc updates
- Before/after evidence summary
- Checklist of what was validated
```

### B) Production-Like AI Bug Triage (Ops-first)

```md
Investigate this AI incident symptom: <symptom>

Use:
- `@docs/OBSERVABILITY.md` for stage-by-stage diagnosis
- `@docs/INCIDENT_RUNBOOK.md` for containment/recovery flow
- `@docs/EVALUATION.md` for validation after fix

Output required:
1) Suspected failing stage (extraction/indexing/retrieval/prompt/generation)
2) Immediate containment action
3) Minimal fix plan
4) Validation steps and rollback note
```

### C) Prompt Update Without Prompt Churn

```md
Update prompt behavior for: <target behavior>

Follow:
- `@docs/PROMPTS.md`
- `@docs/EVALUATION.md`
- `@docs/SECURITY_AI.md`

Rules:
- Do not iterate prompts blindly.
- First diagnose retrieval/context quality.
- Propose one minimal prompt change and why.

Deliverable:
- Prompt diff
- Risk analysis (hallucination, citation, leakage)
- Evaluation evidence plan
```

### D) Frontend + AI Integration Change

```md
Implement this feature touching UI + RAG: <feature>

Use:
- `@AGENT.md`
- `@docs/OBSERVABILITY.md`
- `@docs/RELEASE_CHECKLIST.md`
- Relevant files: <@receipt_ai/pages/...>, <@receipt_ai/features/chat/...>

Requirements:
- Keep `.web/` untouched (generated).
- Add required telemetry/logging touchpoints (non-sensitive).
- Validate route behavior and AI response quality.

Return:
- Changed files
- How observability/release checks were satisfied
```

## 9) Copy-Paste Starter Prompt (Recommended Daily Default)

```md
Task: <one-sentence goal>

Context:
- Follow `@AGENT.md`
- Follow docs relevant to this task: <@docs/...>
- Relevant code files: <@file1>, <@file2>

Constraints:
- Keep change scoped and architecture-safe.
- No unrelated refactors.
- Include tests/evaluation evidence if behavior changes.

Verification:
- Commands/tests to run: <list>
- If AI change: include `docs/EVALUATION.md` + `docs/RELEASE_CHECKLIST.md` checks.

Deliverable:
- Implement directly
- Return summary, validations, and residual risks
```
