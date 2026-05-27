#!/bin/bash
# PostToolUse hook: when an Edit/Write/MultiEdit lands a file under
# ~/agent-skills/dev-skills/skills/, mirror it into every matching plugin
# cache version so the next skill invocation runs the updated copy.
# Exit non-zero only on internal error; never block the tool.
set -e

SRC_ROOT="$HOME/agent-skills/dev-skills/skills"
CACHE_ROOT="$HOME/.claude/plugins/cache/dev-skills/dev-skills"

INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

# Extract tool_input.file_path with jq if present, else a permissive grep fallback.
if command -v jq >/dev/null 2>&1; then
  FILE_PATH=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
else
  FILE_PATH=$(printf '%s' "$INPUT" | sed -n 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
fi

[ -z "$FILE_PATH" ] && exit 0
case "$FILE_PATH" in
  "$SRC_ROOT"/*) ;;
  *) exit 0 ;;
esac
[ -f "$FILE_PATH" ] || exit 0

REL="${FILE_PATH#$SRC_ROOT/}"
for VER_DIR in "$CACHE_ROOT"/*/skills; do
  [ -d "$VER_DIR" ] || continue
  DEST="$VER_DIR/$REL"
  mkdir -p "$(dirname "$DEST")"
  cp -p "$FILE_PATH" "$DEST"
done

exit 0
