#!/bin/bash
# Rename the current Claude Code session by appending a custom-title entry
# to its JSONL file. Mirrors the built-in /rename command's side-effect.
set -e

TITLE="$1"
[ -z "$TITLE" ] && { echo "usage: rename.sh <title>" >&2; exit 1; }

PROJECT_DIR="$HOME/.claude/projects/$(pwd | sed 's|/|-|g')"

if [ -n "$CLAUDE_SESSION_ID" ] && [ -f "$PROJECT_DIR/$CLAUDE_SESSION_ID.jsonl" ]; then
  SESSION_FILE="$PROJECT_DIR/$CLAUDE_SESSION_ID.jsonl"
  SESSION_ID="$CLAUDE_SESSION_ID"
else
  SESSION_FILE=$(ls -t "$PROJECT_DIR"/*.jsonl 2>/dev/null | head -1)
  [ -z "$SESSION_FILE" ] && { echo "no session file found in $PROJECT_DIR" >&2; exit 1; }
  SESSION_ID=$(basename "$SESSION_FILE" .jsonl)
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
