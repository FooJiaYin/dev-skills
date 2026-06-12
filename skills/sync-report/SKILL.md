---
name: sync-report
description: Push a local docs/reports/*.md to a Notion task — appends body, suggests Status, fills Github Link from HEAD. Linked reports (frontmatter `notion.page`) fast-path; unlinked reports get a time-ranked candidate picker with create-new / search-deeper / cancel branches. Use when the user says "/sync-report", "sync this report to Notion", "push report to Notion", or runs /wrap-up step 6 in a Notion-configured repo.
---

# sync-report — local report → Notion task

Notion is master. One of two skills that write to Notion (the other is `/create-tasks`). Working notes in `docs/tasks/<slug>.md` never sync — only the report body does.

## Inputs

- `/sync-report <path>` → that file.
- `/sync-report` (no arg) → most-recent `docs/reports/*.md` by mtime.

## Flow

**1. Config.** Read `AGENTS.md` (preferred) / `CLAUDE.md` `## Notion` → Roadmap DB URL. 

- Missing → dispatch `/setup-notion`, re-read, retry. 
- Still missing → abort. 
- Conflicting URLs across files → prefer `AGENTS.md` silently.

**2. Read report.** Split frontmatter from body. Capture `notion.page`, H1, body, and `# Result` / `# Unsolved Issues` for Status inference.

**3. Resolve target.**
- **Linked** (`notion.page` set) → use it, skip 4–5. To re-target, user edits frontmatter manually.
- **Multi-feature report** (ships several distinct features — multiple `# Changes Made` blocks / a session of several fixes): one report → **multiple tasks**, not one. If a `/create-tasks` backlog exists (`docs/tasks/*-feature-list-backlog.md`, mapping every feature → `〔notion:<id>〕`), grep it per feature name → `〔notion:<id>〕` to resolve targets directly (exact, skip the time query + picker). Then **run steps 6–8 per matched task**, scoped to that feature (its commit for Github Link, its section for the append). Fall through to step 4 only for features with no backlog match.
- **Unlinked, single-feature** → step 4.

**4. Query candidates** (unlinked, single-feature). Compute `reportDate` from filename `YYYY-MM-DD-<slug>.md` (fall back to mtime). Query Roadmap for tasks where `Time` overlaps `[reportDate − 3d, reportDate + 7d]`. No-`Time` tasks excluded here.

**5. Picker** (unlinked only). 

Rank candidates by:
1. `Time` exact-overlap with `reportDate` (high)
2. Semantic match between report H1 + body opening and task Name (high)
3. `Time.end` recency (medium)
4. `Status != Completed`

Show top 8 via `AskUserQuestion`:
- Columns: `Name · scope · Status · Time`. - - Options:
  - Pick a candidate → step 6.
  - Create new → `notion-create-pages` in Roadmap with `Status=Completed 🙌`, `Type=Task 🔨`, `Assignee=me` (from `~/.claude/memory/notion-me.md`; prompt via `/fetch-task` flow if missing), `Project=` prompt, `Release=`current quarter, **body = full report body verbatim (copy-paste; no rewriting, no skipping, no omitting any sections)** (no `# Context` — no meeting source), `Time` blank. Continue at step 6; **skip step 8** (body already written). **Create-coercion (Assignee + Time):** `notion-create-pages` silently coerces several properties — a guest `Assignee` → a workspace member, and `Time`/date → today (dropping `end`) — returning `{page_id}` with no error. `update_properties` is NOT coerced. Don't waste tokens on a verify-fetch: **immediately after create, fire ONE `update_properties` unconditionally re-asserting `Assignee` + `Time` (`date:Time:start` + `date:Time:end`, `is_datetime:0`)** — blind re-write, no re-fetch needed.
  - Search deeper → re-query without time filter, include no-`Time` tasks; same ranking minus time weight.
  - Cancel → exit.

**6. Status suggestion.** 

Scan the report body for signals; propose a status from the live status options:

| Signal | Suggested status |
|---|---|
| `# Result` says "no errors" / "all tests passed" / "shipped"; no `# Unsolved Issues` | `Completed 🙌` |
| "manual testing required" / "needs QA" / `# Unsolved Issues` present | `Testing` |
| "ready for review" / "PR opened" | `In Review` |
| Ambiguous | no change |

`AskUserQuestion`: `Apply <suggestion>` / `Override` (sub-prompt with all options) / `Skip`.

**7. Github Link.** First URL property on Roadmap matching `github` → `pr` → `commit` (case-insensitive). 

None or Target's current value non-empty → skip silently (never overwrite). 

Detect URL: 
1. `/wrap-up` session HEAD commit/PR
2. last 5 commits with messages matching report H1/slug
3. most-recent PR on current branch. 
4. None → skip. 

Build the URL **even if the commit is local/unpushed** — resolve the GitHub base from `git remote -v` (`…:OWNER/REPO.git` → `https://github.com/OWNER/REPO`) + `/commit/<full-sha>`. Unpushed is not a reason to skip; only skip if there's no GitHub remote.

If detected, `AskUserQuestion`: `Apply <url>` / `Skip`.

**8. Append body.** Skip if step 5 took `[n]`. Otherwise `notion-fetch` target, then `notion-update-page` `update_content` with one op: `old_str` = last non-empty line of current body (stable anchor), `new_str` = same anchor + `\n\n` + the full report body (frontmatter stripped, nothing else removed). Verbatim copy-paste. Never rewrite, summarize, rephrase, reformat, skip, or omit any section of the body — even minor cleanup is forbidden. No divider. Fold Status + Github Link from steps 6–7 + `Time` (= report/work date) into the same `update_page` call as `update_properties`. For `Time`, write **both `date:Time:start` AND `date:Time:end`** (`is_datetime:0`) — omitting `end` leaves a stale/empty end on a range.

**Re-sync (linked target already has body) → append only the DELTA, never the whole body.** When the target already contains the report (e.g. `notion.page` was set on a prior sync and you're re-running after adding a new section), `notion-fetch` the body and diff against the local report: identify the section(s) present locally but **not yet in Notion** (typically a freshly-appended `# Updates` / trailing section). Insert only that delta via `notion-update-page` `insert_content` with `position:{type:"end"}`. If the body has no new content, skip the append entirely. Re-pasting the full body duplicates everything (Notion has no clean edit/replace path) — so the verbatim-full-body rule above applies to the FIRST sync only; subsequent syncs are delta-only.

> **Property-name foot-gun:** the `userDefined:` prefix is ONLY for properties literally named `id` or `url` (case-insensitive). Property *types* that hold URLs — `Github Link`, `Slack Link`, `Spec URL`, etc. — use their plain name. A wrongly-prefixed property is silently ignored: the API returns `{page_id}` with no error, but the field stays empty. After writing properties, re-fetch and verify each field changed before claiming success.

**9. Frontmatter write-back.** Update local report: set/refresh `notion.page` (in case 5 picked/created) and `notion.last_synced = <now>`. Body unchanged. Minimal in-place edit.

**10. Commit prompt.** If the report file has uncommitted changes, `AskUserQuestion`:
- `Commit now` — stage + commit `report: <slug> + notion sync`.
- `Amend HEAD` — only if HEAD is this session's wrap-up commit. `git commit --amend --no-edit -- <report>`.
- `Skip — commit later`.

No uncommitted changes → skip silently.

## Hard constraints

- **No writes before confirmation** on picker (unlinked) or Status / Github Link prompts (linked or unlinked).
- **Linked fast path skips the picker.** Frontmatter `notion.page` is authoritative.
- **Never overwrite a non-empty Github Link.**
- **Never overwrite Status without explicit confirmation.**
- **Body append is verbatim copy-paste.** Never rewrite, summarize, rephrase, reformat, skip, or omit any section.
- **Frontmatter stripped before sending to Notion.**
- **`[n]` branch puts report body directly into task body** (no `# Context`) and skips step 8.

## Notes

- Re-syncing is delta-only (step 8): a linked re-sync appends just the new section(s) via `insert_content`, not the whole body. A full-body re-paste would duplicate (Notion has no clean edit/replace path) — avoid it.
- No `content_hash` detection. No multi-URL Github Link.
