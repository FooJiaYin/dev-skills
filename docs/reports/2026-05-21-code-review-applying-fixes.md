# Add "Applying Fixes" guidance to /code-review skill

# Description

- Capture the convention that fix-up after `/code-review` should spawn one subagent per file in parallel, so it travels with the skill instead of living only in user-local memory.

# Changes Made

- Added a brief **Applying Fixes** section above **Critical Rules** in `skills/code-review/SKILL.md`. After several rounds of trimming, the final form is two sentences:

  ```
  ## Applying Fixes

  If the user asks to fix the findings after `REVIEW.md` is written: group findings by file, spawn one subagent per file in a single parallel tool-call block, each receiving all findings for its file. Serialize cross-file findings (e.g. signature changes that ripple to callers) into one agent.
  ```

- Wrote a backup memory entry at `~/.claude/projects/-Users-unilife-agent-skills/memory/feedback_code_review_fix_parallel.md` with the same rule plus `Why:` / `How to apply:` framing. Indexed in `MEMORY.md`. Kept as a per-machine fallback even though the skill file is the source of truth.

Result: Success.

# Updates

- Considered three places for the rule (memory only / new `/apply-review` skill / fold into `/code-review`). Picked the in-skill option after the user pointed out memory isn't sharable and rejected adding a separate skill.
- First draft of the section was a 5-bullet list. Trimmed to two sentences on user request ("shorter").

# Result

- File touched: `skills/code-review/SKILL.md` (+6 lines net).
- No tests, no doc-site, no deploy. Skill is read-only by design; this edit only adds guidance for the follow-up fix step.
