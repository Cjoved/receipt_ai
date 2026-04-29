# Chat Phase Manual Checklist

Use this checklist for demo-readiness verification after running `uv run reflex run`.

## End-to-End Flow

- Login with a valid user account.
- Open Files page and select a folder with at least one indexed file (`Index` column is `completed`).
- Go to Chat page.
- Send one prompt in **Normal** mode.
- Send one prompt in **Thinking ON** mode.
- Confirm assistant replies render with a mode badge (`Normal` or `Reasoning`).
- Confirm source chips appear below assistant replies when retrieval has hits.

## Interaction and Reliability

- Press `Enter` in composer: should send message.
- Press `Shift+Enter`: should insert newline (not send).
- Confirm thread auto-scrolls to newest assistant turn.
- Trigger an error (e.g. bad API key), then click `Retry` on assistant error card after fixing config.
- Confirm retry appends a new assistant response and clears retry state after success.

## Persistence Checks

- Refresh browser tab.
- Re-open same conversation from History.
- Confirm assistant messages persist.
- Confirm citation chips/source metadata persist for past assistant turns.
- Confirm new sends still work after reload in both Normal and Thinking modes.
