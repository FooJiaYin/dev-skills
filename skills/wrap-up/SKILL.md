---
name: wrap-up
description: Post-implementation checklist. Walks through verify → update docs → code-review → generate report → rename session → commit (PR optional). Use when the user says "wrap up", "finalize feature", "ready to ship", "done with this feature", or invokes /wrap-up.
---

# wrap-up — post-implementation checklist

Run these steps in order. Stop and surface failures rather than pushing through.

## 1. Verify correctness

- Invoke `/verify` (the `verify` skill) to execute the implementation plan's Test plan section. It handles plan lookup, skip-if-already-run, command resolution, and per-item pass/fail reporting.
- Wait for `/verify` to finish. If any check fails, **stop here** — do not continue to later steps until the user resolves it.

## 2. Update docs

- Invoke `/update-docs` (the `update-docs` skill) scoped to the current diff. That skill detects the project's doc layout, proposes a per-file update plan, and waits for confirmation before editing.
- Wait for `/update-docs` to finish before continuing.

## 3. Code review

- Invoke `/code-review` (the `code-review` skill) to run a multi-agent review of the diff (including the doc updates from step 2). It writes findings to `REVIEW.md` filtered through a confidence threshold.
- Read `REVIEW.md`. If it has `status: issues_found`, surface the findings to the user and pause for them to decide which to fix.
- Items the user fixes: fix them, then re-run `/code-review` to confirm. Items the user defers: note them so step 4 (report) carries them into the report's `# Unsolved Issues` section. Items the user fixed during this step go into the report's `# Updates` section.
- Wait for `/code-review` and any user fixes to finish before continuing.

## 4. Generate report

- Invoke `/report` (the `report` skill) to capture what was done — conversation, file changes, actions — into `docs/reports/YYYY-MM-DD-[title].md`.
- Skip if the change is trivial (typo, single-line fix) or the user opts out.

## 5. Session hygiene

- After saving the report (and any plan integration), invoke the `rename-session` skill with the report's `YYYY-MM-DD-[title]` as the argument so the session name matches the report. For multiple reports, use the first report's title.

## 6. Commit (PR optional)

- Stage specific files (avoid `git add -A`, which can grab secrets or unrelated junk).
- Write the commit message focused on **why**, not what. Follow the repo's existing commit style (check `git log` for tone).
- Commit.
- **Do not open a PR by default.** After the commit, ask the user: *"Open a PR?"*
  - If yes: confirm before pushing, then push and run `gh pr create` with a summary + test plan.
  - If no: stop here.
- ASK FIRST before any push, force-push, or destructive git operation.

## Guardrails

- Match the global "executing actions with care" rules.
- If `/verify` reports any failure, stop the wrap-up flow.
- Never push or open a PR without explicit user confirmation.
