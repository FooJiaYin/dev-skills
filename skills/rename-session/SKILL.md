---
name: rename-session
description: Rename the current Claude Code session with a short, descriptive title derived from conversation context. AUTO-INVOKE (no confirmation) after generating a report or when a session is newly forked/started. ASK THE USER FIRST before invoking when a major task completes or when the session name is generic/unreadable.
argument-hint: "[optional title]"
---

Rename the current session by appending a `custom-title` entry to its JSONL file — the same mechanism the built-in `/rename` uses.

## Steps

1. Determine the title:
   - If an argument was provided, use it directly.
   - Otherwise, derive a concise title (2–5 words, kebab-case) from the conversation's main topic or the most recent report filename (`YYYY-MM-DD-title`).

2. Run the helper script, quoting the title:

   ```bash
   bash ~/.claude/skills/rename-session/rename.sh '<TITLE>'
   ```

3. Confirm to the user that the session was renamed. Note: the VS Code sidebar may show the old name until a window reload.

## Triggers

- AUTO-INVOKE after generating a report or when a session is newly forked/started.
- ASK THE USER FIRST before invoking when a major task completes or when the session name is generic/unreadable.

## Notes

- The script writes `{"type":"custom-title","customTitle":"...","sessionId":"..."}` to the current session's JSONL at `~/.claude/projects/<encoded-cwd>/<session-id>.jsonl`.
- Claude Code reads the latest `custom-title` entry on session load.
