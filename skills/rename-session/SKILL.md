---
name: rename-session
description: Rename the current Claude Code or Codex session with a short, descriptive title derived from conversation context. AUTO-INVOKE (no confirmation) after generating a report or when a session is newly forked/started. ASK THE USER FIRST before invoking when a major task completes or when the session name is generic/unreadable.
---

**Arguments:** `[optional title]`

Rename the current session through the host's supported session interface.

## Steps

1. Determine the title:
   - If an argument was provided, use it directly.
   - Otherwise, derive a concise title (2–5 words, kebab-case) from the conversation's main topic or the most recent report filename (`YYYY-MM-DD-title`).

2. Detect the host from environment variables, then run the matching helper with the title quoted.

   **Codex** (`CODEX_THREAD_ID` or `CODEX_SESSION_ID` is set):

   ```bash
   python3 <dev-skills-root>/bin/codex-session.py rename '<TITLE>'
   ```

   The helper uses `thread/name/set`, reads the thread back, and fails if the saved title differs. A sandboxed host may require approval because the short-lived app-server opens state under `~/.codex`.

   **Claude Code**:

   ```bash
   bash rename.sh '<TITLE>'
   ```

   The script derives the project dir from `pwd`. Invoke it from the session's original cwd (the one announced at session start), not from a subdirectory you may have `cd`-ed into for earlier steps. If unsure, use a subshell: `(cd "$ORIGINAL_CWD" && bash rename.sh '<TITLE>')`.

3. Confirm to the user that the session was renamed. Note: the VS Code sidebar may show the old name until a window reload.

## Triggers

- AUTO-INVOKE after generating a report or when a session is newly forked/started.
- ASK THE USER FIRST before invoking when a major task completes or when the session name is generic/unreadable.

## Notes

- The Codex helper requires an explicit ID from `CODEX_THREAD_ID`, `CODEX_SESSION_ID`, or `--thread`; it never guesses the newest session or edits Codex SQLite/rollout files directly.
- The script writes `{"type":"custom-title","customTitle":"...","sessionId":"..."}` to the current session's JSONL at `~/.claude/projects/<encoded-cwd>/<session-id>.jsonl`.
- Claude Code reads the latest `custom-title` entry on session load.
