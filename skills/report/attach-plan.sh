#!/bin/bash
# Usage: attach-plan.sh <prepend|append> <plan-file> <report-file>
#   prepend — insert plan under a "# Plan" heading after the report's title line
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
  tmp=$(mktemp)
  head -n 1 "$report_file" > "$tmp"
  echo "" >> "$tmp"
  echo "# Plan" >> "$tmp"
  echo "" >> "$tmp"
  cat "$plan_file" >> "$tmp"
  echo "" >> "$tmp"
  echo "---" >> "$tmp"
  echo "" >> "$tmp"
  tail -n +2 "$report_file" >> "$tmp"
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
