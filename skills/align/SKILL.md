---
name: align
description: Check that what's being built matches what was asked, across the requirement chain transcript → meeting notes → task file → plan (any stage may be missing). `start` before writing/approving a plan; `end` at wrap-up to check the baseline item by item and write unfinished / untested / open questions to TODO.md. Use when the user says "/align", "對齊需求", "有沒有漏掉會議的東西", "check against the meeting", "did we miss anything from the meeting"; invoked by plan mode (start), /create-tasks (light start) and /wrap-up Full/Quick (end).
---

# align — requirement chain vs. what gets built

**Rule:** run the work end to end unless the user asked to split it. Unfinished work, untested items and open questions go to `TODO.md` — never only into chat or a report.

Arguments: `start` | `end` | `end --quick` (non-interactive). Callers: plan mode runs `start` before the plan is written; `/create-tasks` runs a light `start` (meeting notes → task only); `/wrap-up` Full runs `end`, Quick runs `end --quick`.

## 1. Find the stages

Collect whichever exist; skip missing stages silently.

| Stage | Where |
|---|---|
| transcript | the meeting note's `資料來源` / `Source` / `Transcript` reference, then sibling `<basename>-transcript.*` (same order as `/upload-meeting` §4b) |
| meeting notes | `docs/meetings/*.md`; meetings mentioned in the task's `# Context` |
| task | `docs/tasks/<slug>.md` (its `# Context` holds the meeting excerpts) |
| plan | this session's plan file, `docs/plans/`, `docs/tasks/_plan-*.md` |

If several candidates fit, pick by the task / topic of this session; ask only when still ambiguous.

## 2. `start`

1. **Baseline = the furthest stage that exists.** Extract its items: each concrete requirement, including UI placement, appearance and wording ("put it next to X", "like the tax field") — those get lost first.
2. Compare against **one stage back** (plan ↔ task, task ↔ meeting notes, notes ↔ transcript). Go to the transcript only when an item is ambiguous or the notes look compressed.
3. Every item present upstream but missing or weakened downstream → `AskUserQuestion` (batch up to 4 items per call), options: **Add to baseline** / **Covered by another task** (user names it) / **Move to TODO.md**. Nothing drops silently.
4. Write `## Baseline` at the end of the plan (or the task file when there is no plan; never inside the task's managed `# Context`):

```markdown
## Baseline
- B1 <item> — <stage>: "<short quote>"
- B2 …
### Excluded
- <item> — in task <name> | → TODO.md — <stage>: "<short quote>"
```

**Light start** (`/create-tasks`): only meeting notes → tasks; every commitment ends as a task, an explicit skip with a reason, or a TODO.md item.

## 3. `end`

1. Read `## Baseline`. If none, derive one from the furthest stage now and say so.
2. For each item give status + evidence: ✓ only with a test name, screenshot path, or `file:line`; no evidence = **untested** (?); not done = ✗. Show a table: `# | item | status | evidence`.
3. Against the diff, also flag (from the retired plan-adherence check):
   - **Missing** — baseline / plan item the diff doesn't do.
   - **Scope creep** — non-trivial change no stage asked for (renames and refactors that follow from planned work don't count).
   - **Out-of-scope violation** — the plan said not to touch it.
   - **Undocumented breaking change** — changed/removed exported symbol, endpoint, CLI flag or schema, or a migration with no migration/rollback note in the plan.
4. Every ✗ / ? / flag → TODO.md (§4). Interactive `end` may ask about genuinely ambiguous flags; `--quick` asks nothing and writes them straight in.
5. Close with TODO.md items **related to this change** (delete those it finished, with evidence) and items **untouched > 14 days** (by the item's date; fall back to `git log` on the line).

## 4. TODO.md

Create at repo root if missing:

```markdown
# Unsolve Issues
# Chores
# Documentation
# Manual Test
# Questions and Resources
```

- One item per line: `- [ ] <item>（來源：<stage/file>，<YYYY-MM-DD>）`. If the item has a Notion task, the source is the task link. Delete items when done — no ✓ history.
- Several sessions write `TODO.md` at the same time, so use additive `Edit` only, and re-read the file right before each write.
- Group items by the kind of next step, not by feature. Unsolve Issues = needs a code change. Chores = merge, deploy, cleanup, credentials, test data. Documentation = docs, Notion tickets, meeting pages. Manual Test = already built or deployed, and someone needs to click through and confirm. Questions and Resources = decisions the client or PM must make, or materials we need from them.
- If one item has two kinds of next step, split it into two lines. Add `##` feature subheadings only when a section gets long.
- If TODO.md already exists, keep its structure and language: put items in its closest-matching section, add a missing section only when nothing fits, and write items in its language.
