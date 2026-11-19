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

**Walk up parent directories, not just the repo root.** Org-shared Notion config often lives one or two levels above the repo (e.g. `~/work/<org>/AGENTS.md` covering several sibling repos). Check the repo root first, then each ancestor up to `$HOME`, and take the nearest hit.

**Before concluding "no Notion config", cross-check for evidence Notion is in use:** `grep -l "^notion:" docs/reports/*.md` (or any `notion.page` frontmatter). If past reports are linked but no `## Notion` block was found, the config exists somewhere you haven't looked — widen the search or ask the user where it lives. Do NOT silently skip the sync. (Seen: config sat in the parent dir's `AGENTS.md`; the skill reported "no Notion config" and skipped, and the user had to correct it.)

- Missing → dispatch `/setup-notion`, re-read, retry. 
- Still missing → abort. 
- Conflicting URLs across files → prefer `AGENTS.md` silently, then the nearest ancestor.
- Roadmap fetch returns 404 / `object_not_found` → call `notion-get-self` at once and tell the user which workspace the connection is signed in to; ask them to reconnect Notion to the Roadmap's workspace (`/mcp`), then re-run. Don't report it as a missing database or retry. If the repo or an ancestor has a `.env` with `NOTION_TOKEN` (or the Notion config says to use one), offer that as the alternative: call the Notion API with the integration token directly — it doesn't depend on which account the MCP is signed in to.

**2. Read report.** Split frontmatter from body. Capture `notion.page`, H1, body, and `# Result` / `# Unsolved Issues` for Status inference.

**3. Resolve target.**
- **Linked** (`notion.page` set) → use it, skip 4–5. To re-target, user edits frontmatter manually.
- **Multi-feature report** (ships several distinct features — multiple `# Changes Made` blocks / a session of several fixes): one report → **multiple tasks**, not one. If a `/create-tasks` backlog exists (`docs/tasks/*-feature-list-backlog.md`, mapping every feature → `〔notion:<id>〕`), grep it per feature name → `〔notion:<id>〕` to resolve targets directly (exact, skip the time query + picker). Then **run steps 6–8 per matched task** (the append through 8b), scoped to that feature (its commit for Github Link, its section for the append). Fall through to step 4 only for features with no backlog match.
- **Unlinked, single-feature** → **first check `docs/tasks/*.md` for files with `notion.page` frontmatter** (tasks someone already `/fetch-task`'d). If any exist, offer them as the top candidates (Name · Time) before the time-window picker — a fetched task that matches the report's topic is almost always the intended target, and the time-window query alone misses it (seen: picker offered a sibling task while the real target sat in `docs/tasks/`, user had to `@` it by hand). None → step 4.

**4. Query candidates** (unlinked, single-feature). Compute `reportDate` from filename `YYYY-MM-DD-<slug>.md` (fall back to mtime). Query Roadmap for tasks where `Time` overlaps `[reportDate − 3d, reportDate + 7d]`. No-`Time` tasks excluded here.
 **`notion-query-database-view` has no filter param — it dumps the full view (often >token cap; the result is saved to a file). Don't read it inline: parse the saved file by Time window with python/jq on `date:Time:start` / `date:Time:end` (+ `Name` / `Status` / `url`).**

**5. Picker** (unlinked only). 

Rank candidates by:
1. `Time` exact-overlap with `reportDate` (high)
2. Semantic match between report H1 + body opening and task Name (high)
3. `Time.end` recency (medium)
4. `Status != Completed`

Show top 8 via `AskUserQuestion`:
- Columns: `Name · scope · Status · Time`. - - Options:
  - Pick a candidate → step 6.
  - Create new → **two calls, properties first**: `notion-create-pages` with properties ONLY (no `content`), read the returned properties back, then append the body with step 8 (script; MCP fallback: `notion-update-page` `insert_content` `position:{type:"end"}`). A property-validation error rejects the whole payload, so sending a multi-KB body alongside untested properties means re-transmitting the entire report on any format slip. **Property formats that silently or loudly fail:** `date:*:is_datetime` must be a JSON **number** `0`/`1`, not the string `"0"`; `Assignee` / `Project` / any relation or person property must be a real **array** (`["<id>"]`), not a JSON-encoded string (`"[\"<id>\"]"`). Set properties as `Status=Completed 🙌`, `Type=Task 🔨`, `Assignee=me` (from `~/.claude/memory/notion-me.md`; prompt via `/fetch-task` flow if missing), `Project=` prompt, `Release=`current quarter, **body = full report body verbatim (copy-paste; no rewriting, no skipping, no omitting any sections)** (no `# Context` — no meeting source), `Time` blank. Continue at step 6; step 8 appends the body. **Create-coercion (Assignee + Time):** `notion-create-pages` silently coerces several properties — a guest `Assignee` → a workspace member, and `Time`/date → today (dropping `end`) — returning `{page_id}` with no error. Immediately after create, fire ONE `update_properties` re-asserting `Assignee` + `Time` (`date:Time:start` + `date:Time:end`, `is_datetime:0`). **That blind re-write is not sufficient — verify it.** `update_properties` returns `{page_id}` with no error yet silently fails to persist (observed repeatedly: guest `Assignee` reverts to the OAuth account, dates stay at today). Confirm with **one `notion-query-data-sources` SQL read-back** covering the rows you just wrote (Name, Status, Time, Assignee) and repair whatever disagrees — one query is cheap even at batch size, per-page `notion-fetch` is not. Note also that **omitting `Time` does not leave it blank**; a row that should have no date needs an explicit `"date:Time:start": null`.
  - Search deeper → re-query without time filter, include no-`Time` tasks; same ranking minus time weight.
  - Cancel → exit.

> **Ambiguous / custom reply → re-ask, don't assume.** If the user's answer is a free-text/`Other` reply (not a clean pick of a listed option) or implies a different shape than the picker offered (e.g. "both new task", "separate uploads", "split into N tasks"), the new-vs-existing decision is **not settled** — re-ask (new vs existing, and how many targets) and get an explicit target BEFORE any `notion-update-page` / append / create. **Never append a report to an existing task on an inferred/unconfirmed target** — a wrong append is costly (Notion has no clean undo; you must hand-reconstruct the exact inserted markdown to remove it).

**6. Status suggestion.** 

Scan the report body for signals; propose a status from the live status options:

| Signal | Suggested status |
|---|---|
| `# Result` says "no errors" / "all tests passed" / "shipped"; no `# Unsolved Issues` | `Completed 🙌` |
| "manual testing required" / "needs QA" / `# Unsolved Issues` present | `Testing` |
| "ready for review" / "PR opened" | `In Review` |
| Report covers only part of the task's scope (enabling piece; the task's main work not done) | `In Progress` |
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

**8. Write — script first.** Writes go through `bin/notion-io.py`, so the report body never passes through the model:

```
python3 <dev-skills-root>/bin/notion-io.py sync-report <report.md> [--page <task url>] \
  [--status "<confirmed status>"] [--github <confirmed url>] [--time <start> [<end>]] [--dry-run]
```

`--page` defaults to frontmatter `notion.page`; pass only the values the user confirmed in steps 6–7, and `--time` = report/work date (start and end). The script drops leading sections already on the task (normally `# Context`), uploads every `![caption](file)` line as an image block, appends the rest at the end of the page, writes the properties and reads them back (it never overwrites a non-empty Github Link), then sets `notion.last_synced` — so skip step 9's write-back. A failed run leaves `<report>.sync.json`; rerun the same command to resume. Read only its summary. Exit codes:
- `2` — input to fix, e.g. an image inside a table or list item: move each screenshot onto its own line in the report, then rerun.
- `4` — needs the user: the task already has this report (re-sync), or a section with the same heading differs. Ask; `--skip "<H1>"` leaves that leading section out (e.g. the task's `# Context` is newer), `--force` appends from it on. A summary note "already has `# X`" (typically `# Unsolved Issues`) → apply 8b's never-leave-two rule to the old section. For a re-sync, append only the new section(s) yourself (delta rule below).
- `1` — a write failed; report the message, don't resend blindly.
- `3` — no token → MCP fallback below.

**8b. MCP path** — exit 3, or a multi-feature report (the script appends the whole body; scope each task's append by hand here). `notion-fetch` target and compare its content with the report body after stripping frontmatter. A report produced from a fetched task normally starts with the same managed `# Context` already present on that task: treat each identical leading top-level section as existing content and exclude it from the append. Preserve the remaining suffix byte-for-byte. If the overlap is ambiguous rather than identical, stop and ask instead of duplicating or dropping content. If the target already has a `# Unsolved Issues` section (created with the task) and the report has its own, the report's version replaces it — delete the old section in the same `update_content` call (one more op) after confirming each old item is resolved or carried over; never leave two. Then call `notion-update-page` `update_content` with one op: `old_str` = last non-empty line of current body (stable anchor), `new_str` = same anchor + `\n\n` + the remaining report body. Verbatim copy-paste. Never rewrite, summarize, rephrase, or reformat content; omit only an identical leading section already present on the target. No divider. Write Status + Github Link from steps 6–7 + `Time` (= report/work date) in a **separate** `update_page` `update_properties` call — folded into the `update_content` call they are silently dropped — then read them back with one `notion-query-data-sources` SQL query and repair what disagrees. For `Time`, write **both `date:Time:start` AND `date:Time:end`** (`is_datetime:0`) — omitting `end` leaves a stale/empty end on a range.

**Cloudflare WAF in front of Notion rejects HTML-tag literals.** A body containing a literal `<script>` (likely also `<iframe>`, `<img …>`, `<object>`) gets a 403 "Sorry, you have been blocked" page with no hint of the offending string — the whole insert fails. Before sending: grep the body for `<script`, `<iframe`, `<img`, `<object` and replace those tokens with full-width brackets (`＜script＞`); say so in the final message as the one non-verbatim change. For bodies over ~8 KB, `insert_content` in section-sized chunks, sequentially (each `position: end`), so a rejected chunk isolates the culprit and already-inserted chunks are not re-sent (re-sending duplicates; Notion has no clean undo).

**Images and artifacts go up too — the user expects them on the task, not only in the repo.** Images never go inside a table or list item (Notion rejects the whole body: "Inline image Markdown is not supported in rich text") — upload first, then send each as its own `<image>` block with the body. After the body append, for every local image the report references (`![…](…)`, normally under `## 畫面` at the end of `# Verification`) and every file in its `<report>-artifacts/` folder that a reader would open (screenshots, HTML report pages; skip scripts): `notion-create-file-upload` → POST the file to the returned `upload_url` with curl (`-F "file=@<path>;type=<mime>"`, the returned auth header) **in the same turn** — the upload URL expires within minutes, so create ≤3 and send them before creating more. Then place each within the hour (unplaced uploads are deleted): images as `<image source="file-upload://<id>">caption</image>` under `## 畫面` at the end of `# Verification` (before `# Result`), HTML as `<embed source="file-upload://<id>" />`. Re-fetch and confirm each became a `notion-file-block://` source.

**Re-sync (linked target already has body) → append only the DELTA, never the whole body.** When the target already contains the report (e.g. `notion.page` was set on a prior sync and you're re-running after adding a new section), `notion-fetch` the body and diff against the local report: identify the section(s) present locally but **not yet in Notion** (typically a freshly-appended `# Updates` / trailing section). Insert only that delta via `notion-update-page` `insert_content` with `position:{type:"end"}`. If the body has no new content, skip the append entirely. Re-pasting the full body duplicates everything (Notion has no clean edit/replace path) — so the verbatim-full-body rule above applies to the FIRST sync only; subsequent syncs are delta-only.

**`update_content` anchors: Notion stores inline code as `<code>…</code>`, not backticks** (bold as `<b>`). An `old_str` copied from the local markdown that contains `` ` `` never matches. Anchor on a plain-text fragment, or copy the exact bytes from a `notion-fetch`.

**Notion auto-links bare filenames that look like domains** (`AGENTS.md`, `TODO.md` outside backticks become `[AGENTS.md](http://AGENTS.md)`). After the append, grep the fetched body for `](http://<name>.<ext>)` and unwrap them with one `update_content`.

> **Property-name foot-gun:** the `userDefined:` prefix is ONLY for properties literally named `id` or `url` (case-insensitive). Property *types* that hold URLs — `Github Link`, `Slack Link`, `Spec URL`, etc. — use their plain name. A wrongly-prefixed property is silently ignored: the API returns `{page_id}` with no error, but the field stays empty. After writing properties, re-fetch and verify each field changed before claiming success.

**9. Frontmatter write-back** (MCP path only — the script does it). Update local report: set/refresh `notion.page` (in case 5 picked/created) and `notion.last_synced = <now>`. Body unchanged. Minimal in-place edit.

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
- **Body append is verbatim copy-paste.** Never rewrite, summarize, rephrase, or reformat any section. The only allowed omission is an identical leading top-level section already present on the target (normally a fetched task's managed `# Context`).
- **Frontmatter stripped before sending to Notion.**
- **Section order on the task: `# Context` → `Resource` → `# Plan` → … → `# Updates` → … → `Reference` (last).** `# Resource` = the material the task works from (files are uploaded with `notion-create-file-upload`); `# Reference` = what the work points to (PRs, docs consulted). Add neither when empty.
- **`[n]` branch puts report body directly into task body** (no `# Context`) via step 8, after the properties-only create.

## Notes

- Re-syncing is delta-only (step 8): a linked re-sync appends just the new section(s) via `insert_content`, not the whole body. A full-body re-paste would duplicate (Notion has no clean edit/replace path) — avoid it.
- No `content_hash` detection. No multi-URL Github Link.
