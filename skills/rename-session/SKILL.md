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

2. Run the shared adapter with the title quoted:

   ```bash
   python3 <dev-skills-root>/bin/session-adapter.py rename '<TITLE>'
   ```

   It detects Claude Code or Codex from the session ID environment variables, delegates to that host's supported storage interface, reads the saved title back, and fails if verification differs. For a historical session, pass `--host claude|codex --session <ID>` explicitly. A sandboxed Codex host may require approval because its short-lived app-server opens state under `~/.codex`.

3. Confirm to the user that the session was renamed. Note: the VS Code sidebar may show the old name until a window reload.

## Triggers

- AUTO-INVOKE after generating a report or when a session is newly forked/started.
- ASK THE USER FIRST before invoking when a major task completes or when the session name is generic/unreadable.

## Notes

- The shared adapter requires an explicit ID from the host environment or `--session`; it never guesses the newest session.
- The Codex backend uses the app-server protocol and never edits Codex SQLite/rollout files directly.
- The Claude backend delegates to `rename.sh`, which writes `{"type":"custom-title","customTitle":"...","sessionId":"..."}` to the matching JSONL at `~/.claude/projects/<encoded-cwd>/<session-id>.jsonl`.
- Claude Code reads the latest `custom-title` entry on session load.
