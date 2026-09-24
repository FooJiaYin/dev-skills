#!/bin/bash
# Rename the current Claude Code session by appending a custom-title entry
# to its JSONL file. Mirrors the built-in /rename command's side-effect.
set -e

if [ -n "${CODEX_THREAD_ID:-}" ] || [ -n "${CODEX_SESSION_ID:-}" ]; then
  echo "rename.sh supports Claude Code only; use the Codex host rename capability." >&2
  exit 2
fi

TITLE="$1"
[ -z "$TITLE" ] && { echo "usage: rename.sh <title>" >&2; exit 1; }

SID="${CLAUDE_CODE_SESSION_ID:-$CLAUDE_SESSION_ID}"
SESSION_FILE=""
# Look up by id across all projects — the shell's pwd may have drifted into a subdirectory.
[ -n "$SID" ] && SESSION_FILE=$(ls "$HOME"/.claude/projects/*/"$SID".jsonl 2>/dev/null | head -1)
if [ -n "$SESSION_FILE" ]; then
  SESSION_ID="$SID"
else
  [ -n "$SID" ] || { echo "An explicit Claude session ID is required; refusing to guess the newest transcript." >&2; exit 2; }
  echo "No Claude transcript found for session $SID" >&2
  exit 2
fi

if command -v jq >/dev/null 2>&1; then
  LINE=$(jq -cn --arg t "$TITLE" --arg id "$SESSION_ID" \
    '{type:"custom-title",customTitle:$t,sessionId:$id}')
else
  ESCAPED=$(printf '%s' "$TITLE" | sed 's/\\/\\\\/g; s/"/\\"/g')
  LINE=$(printf '{"type":"custom-title","customTitle":"%s","sessionId":"%s"}' "$ESCAPED" "$SESSION_ID")
fi

printf '%s\n' "$LINE" >> "$SESSION_FILE"
echo "Renamed session $SESSION_ID → $TITLE"
