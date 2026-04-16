# Receipt AI Implementation Roadmap

This document tracks the step-by-step execution order from login to chat history and RAG completion, for next week's presentation.

## Phase 1 - Foundation

- Finalize architecture boundaries:
  - `PostgreSQL` for auth, sessions, chat threads/messages metadata
  - `Qdrant` for vector search
  - `Wasabi` for file storage
  - `Kimi` for extraction + answer generation
- Standardize environment variables and local service startup.
- Freeze MVP demo scope (what must work live).

## Phase 2 - Database Schema

- Add migrations for:
  - `users`
  - `sessions`
  - `conversations`
  - `messages`
  - optional `message_sources`
- Add indexes for user-scoped conversation loading and message ordering.

## Phase 3 - Auth Integration

- Connect login/session flows to DB-backed storage.
- Ensure protected routes validate active sessions.
- Add auth error states (invalid credentials, expired session).
- Keep seeding dev-only with explicit guard (`ALLOW_SEED=true`) and never run in production.

## Phase 4 - Chat Persistence

- Replace in-memory chat history with DB-backed conversations/messages.
- Implement thread create/list/select/delete.
- Persist both user and assistant messages.

## Phase 5 - Retrieval Quality

- Add retrieval score thresholds.
- Add fallback strategy when scoped retrieval is empty.
- Persist source/citation metadata per assistant message.

## Phase 6 - Chat UI Completion

- Auto-scroll to latest turn.
- Enter-to-send and Shift+Enter newline behavior.
- Retry action for failed turns.
- Source chips/cards under assistant replies.

## Phase 7 - Extraction Hardening

- Keep strict receipt validation configurable.
- Improve extraction/indexing error messages in UI.
- Confirm indexing status visibility in files panel.

## Phase 8 - Testing and Stability

- Unit tests for auth/chat state/retrieval logic.
- Integration test for login -> upload -> index -> ask -> reload history.
- Smoke test full local stack (app + postgres + qdrant).

## Phase 9 - Presentation Prep

- Demo script:
  1. Login
  2. Upload
  3. Indexing complete
  4. Chat answer with citations
  5. Refresh and show persisted history
- Architecture slide + risk/mitigation slide.

## Suggested Weekly Order

- Monday: Phase 1-2
- Tuesday: Phase 3-4
- Wednesday: Phase 5
- Thursday: Phase 6-8
- Friday: Phase 9 + dry run
