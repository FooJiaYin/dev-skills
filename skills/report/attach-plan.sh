#!/bin/bash
# Usage: attach-plan.sh <prepend|append> <plan-file> <report-file>
#   prepend — insert plan under a "# Plan" heading after the report's frontmatter
#             (if any) or first title line; preserves YAML frontmatter at top
#   append  — append plan under a "# Final Plan" heading at the end of the report

mode="$1"
plan_file="$2"
report_file="$3"

if [[ "$mode" != "prepend" && "$mode" != "append" ]]; then
  echo "Mode must be 'prepend' or 'append' (got: $mode)" >&2
  exit 1
fi

if [[ ! -f "$plan_file" ]]; then
  echo "Plan file not found: $plan_file" >&2
  exit 1
fi

if [[ ! -f "$report_file" ]]; then
  echo "Report file not found: $report_file" >&2
  exit 1
fi

if [[ "$mode" == "prepend" ]]; then
  # Idempotency guard: if the report already has a top-level "# Plan"
  # heading, refuse to insert a second one. The caller should remove the
  # existing Plan section first (or accept that re-attach is a no-op).
  if grep -q '^# Plan[[:space:]]*$' "$report_file"; then
    echo "attach-plan: '$report_file' already has a '# Plan' section — skipping (no-op)." >&2
    exit 0
  fi

  tmp=$(mktemp)

  # Decide where to insert the "# Plan" section. The head we preserve
  # depends on the report file's shape:
  #
  # 1. Reports that came from `/fetch-task` open with frontmatter + a
  #    `# Context` block synced from Notion. The natural reading order is
  #    Context → Plan → Changes Made → Updates → Result, so we insert the
  #    plan AFTER the entire `# Context` block (everything up to the next
  #    top-level `# ` heading, or EOF if it's the only section so far).
  # 2. Reports with frontmatter but no `# Context` (fresh /report runs):
  #    insert after the closing `---` of the frontmatter.
  # 3. Reports without frontmatter: legacy behavior — insert after line 1
  #    (the title).
  head_lines=1
  if [[ "$(head -n 1 "$report_file")" == "---" ]]; then
    # Find closing `---` of frontmatter.
    close=$(awk 'NR>1 && /^---$/ {print NR; exit}' "$report_file")
    if [[ -n "$close" ]]; then
      head_lines=$close
      # Look for a `# Context` heading and, if found, extend head_lines to
      # cover the whole Context block (up to next top-level `# ` heading
      # OR until EOF).
      ctx_start=$(awk -v after="$close" 'NR>after && /^# Context[[:space:]]*$/ {print NR; exit}' "$report_file")
      if [[ -n "$ctx_start" ]]; then
        next_h1=$(awk -v after="$ctx_start" 'NR>after && /^# / {print NR; exit}' "$report_file")
        if [[ -n "$next_h1" ]]; then
          # Insert just before the next `# `, which means head = next_h1 - 1
          head_lines=$((next_h1 - 1))
        else
          # No next `# ` — Context is the last section. Take the whole file.
          head_lines=$(wc -l < "$report_file" | tr -d ' ')
        fi
      fi
    fi
  fi

  head -n "$head_lines" "$report_file" > "$tmp"
  echo "" >> "$tmp"
  echo "# Plan" >> "$tmp"
  echo "" >> "$tmp"
  cat "$plan_file" >> "$tmp"
  echo "" >> "$tmp"
  tail -n +$((head_lines + 1)) "$report_file" >> "$tmp"
  mv "$tmp" "$report_file"
else
  {
    echo ""
    echo "---"
    echo ""
    echo "# Final Plan"
    echo ""
    cat "$plan_file"
  } >> "$report_file"
fi
