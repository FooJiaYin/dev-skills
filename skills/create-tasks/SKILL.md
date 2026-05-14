---
name: create-tasks
description: Turn a meeting note into Notion tasks. Extracts commitments from the meeting body, classifies each as LINK / DRAFT / SKIP, pre-matches against the Roadmap's Current view, renders a plan-mode preview for user iteration, and on approval creates new tasks, appends meeting context to linked tasks (inside `# Context` only), wires up the meeting's Tasks relation, and rewrites the original commitment text inline as `<mention-page>` references. Use when the user says "/create-tasks", "extract tasks from meeting", "turn this meeting into tasks", or passes a Notion meeting URL / local markdown / pasted notes.
---

# create-tasks — meeting → Notion tasks

Authority: **Notion is master.** This skill is one of only two skills that write to Notion (the other is `/sync-report`).

## Inputs

- A Notion meeting page URL → use as-is.
- A local markdown file path / Google Docs URL / pasted text → run the non-Notion preflight below.

"Source page" throughout the rest of the skill means meeting page, custom parent, or none (Standalone).

## Flow

### 1. Resolve config

Read `AGENTS.md` (preferred) / `CLAUDE.md`. Locate the `## Notion` section. Extract Roadmap DB URL, Meetings DB URL, optional **Meetings title format** line, and optional `### Team` roster.

If either DB URL is missing → dispatch `/setup-notion`, then re-read `AGENTS.md` from scratch and continue. Do not pass state in to setup; do not assume it succeeded — re-validate.

### 2. Resolve input source

If the input is not a Notion URL, run the non-Notion preflight:

### Non-Notion preflight

Meeting-shape heuristic: input is meeting-shaped if ≥2 of {date marker like `2026-` / `日期:` / `## N月`, participant cluster, H2 section structure, length >~30 lines}.

- **Meeting-shaped** → prompt for Title / Date / Participants via `AskUserQuestion`, `notion-create-pages` in the meetings DB. Continue with the new meeting URL.
- **Not meeting-shaped** → `AskUserQuestion` 4-way picker:
  1. **Treat as meeting anyway** → same as meeting-shaped path.
  2. **Standalone tasks** → no source page. Skip steps 9.3, 9.4, 9.5. Each task's `# Context` is the bounding span only (no mention-page prefix). All idempotency anchors inactive — re-runs duplicate; the plan header warns.
  3. **Upload to custom parent** → prompt for a Notion parent page/DB URL. `notion-create-pages` as a child there. The new page URL is the source URL for every task's `# Context` mention-page prefix. If the parent has a `Tasks` relation property → run 9.3 + 9.4 against it. If not → skip 9.3 + 9.4; the per-task mention-page in `# Context` is the only breadcrumb, and idempotency anchors are inactive. Always skip 9.5 (no local mirror for custom parents).
  4. **Cancel** → abort.

From this point, operate on the resolved source page — or, for the Standalone branch, on the raw input text with no source page.

For meeting / treat-as-meeting uploads, follow AGENTS.md's `Meetings title format` for the new page title. Substitute `<date>` from the resolved meeting date and `<topic>` from the input's first H1 or filename. Fall back to just `<topic>` if the pattern line is missing. Custom-parent uploads use the first H1 / filename verbatim as the title.

### 3. Fetch meeting + active task pool

In parallel:
- `notion-fetch` the meeting page → body markdown, Participants, Project relation, **existing `Tasks` relation list** (for idempotency).
- Query the Roadmap's `Current` view by name (exact match; fall back to the first non-Completed view). Collect the ~10–30 active task rows: Name, Status, Assignee, Type, Project, first ~200 chars of body.

Then **mirror the meeting body to `docs/meetings/<YYYY-MM-DD>-<slug>.md`** — the byte-exact source for step 4 extraction.

**Variants.** Standalone: skip the source `notion-fetch` and the local mirror; step 4 reads from the raw input text directly. Custom parent: `notion-fetch` the parent for body markdown + (if present) `Tasks` relation list; skip the `docs/meetings/` mirror.

- `<YYYY-MM-DD>`: (1) Notion date property; (2) date-like marker in body (`日期:`, `## 4月28日 |`); (3) today.
- `<slug>`: meeting title, kebab-case.
- Frontmatter:

  ```markdown
  ---
  notion:
    url: <meeting-page-url>
    last_synced: <ISO-8601 timestamp>
  ---
  [body verbatim from notion-fetch]
  ```

- **Notion is master.** Always overwrite on re-run; local edits are discarded.
- `docs/meetings/` is not gitignored by default — usually worth committing.

### 4. Extract commitments

LLM pass over the source content:

- Identify each engineering commitment (action item, follow-up, "will do X", explicit assignment).
- For each commitment, capture:
  - The **exact verbatim text span** from the meeting body (byte-exact — this becomes the `old_str` anchor later).
  - The **bounding H2 topic section** the commitment lives under.
  - The proposed assignee (resolved from Participants + @-mentions + team roster).
  - A first-pass classification: `LINK` (matches an active task), `DRAFT` (new), `SKIP` (with reason).
- Skip by default: coordination ("X 與 Y 約時間"), admin chores ("update progress doc"), in-line decisions ("結論：方案2"), items already followed by `<mention-page>` in the body, items assigned to non-engineers.

#### Type classification

Pick the `Type` per commitment using this guide. Default to `Task 🔨` only when none of the others fit. Surface the chosen Type in the plan.

- **⛰️ Feature** — larger functionality that will fan out into sub-tasks. Examples: "App 改版 v3.0", "電商功能". Body should reference design, priority, related docs.
- **🐞 Bug** — something currently broken. Examples: "圖片寬度不一致", "新聞網閃退問題". Body holds error messages, screenshots, root-cause notes once known.
- **🔨 Task** — smaller, self-contained work that can be completed in one go. Examples: "更換愛心 icon", "優惠券顯示圖片". The default fallback.
- **🧪 Test** — testing record for a specific version (e.g. v0.5 內測). Includes the small adjustments captured after demo.
- **🔎 Survey** — we don't yet know how to do it; we need to compare approaches/tools/libraries. Examples: "State Management Library", "SEO 優化".
- **📄 Documentation** — explicit "write up X" / "document Y" / "draft contract Z" commitments.
- **Request** — outbound asks to other teams or external parties.

Cue words that bias the choice:

- "修正 / 修復 / 壞掉 / fix / broken" → `Bug 🐞`
- "改版 / 設計 / 規劃 / overhaul / new module" → `Feature ⛰️`
- "調查 / 比較 / 評估方案 / research / spike" → `Survey 🔎`
- "撰寫 / 寫一份 / 草擬 / draft / write up" → `Documentation 📄`
- "測試 / 驗證 / smoke test / regression" → `Test 🧪`

#### Time extraction

Set when the commitment text or its row/section names a deadline (`明日`, `下週四`, `by Friday`, `2026-04-30`). Normalize to ISO date; anchor relative phrases to the meeting date (`明日` = meeting date + 1). Range only if explicit. Leave blank when no deadline is mentioned.

#### Assignee resolution

Lookup order (stop at first hit). Each source determines the `(member)` / `(guest)` tag carried through to step 9 (controls create-pages vs post-create update fan-out).

1. **`### Team` roster in AGENTS.md** — exact match. Tag from the roster line. No remote call.
2. **`notion-get-users`** — name/email match → `(member)`.
3. **`notion-search` `query_type=user`** — name/email match → `(guest)`.
4. **`AskUserQuestion`** — fuzzy/ambiguous. Skip only when (1) hits exactly.

**Update roster.** On each new confirmation (via 3 or 4), append to `### Team` immediately:

```
- <Display Name> <email@example.com> — <notion-user-id> (member|guest)
```

Eager — not batched. Plan in step 7 reflects the cached state; later commitments in the same run hit (1).

### 5. Idempotency anchors

Before rendering the plan, classify each commitment against two anchors. Both require a source page with a `Tasks` relation. Skip for Standalone (no source).

- **Primary anchor**: the meeting's existing `Tasks` relation. Any task already in the relation gets a separate `ALREADY-LINKED` row in the plan (read-only, for visibility), not re-processed. Skip if no `Tasks` relation.
- **Secondary anchor**: a commitment whose extracted text is **immediately followed by a `<mention-page>` reference** in the meeting body → `ALREADY-LINKED`. The inline annotation marks it; the relation is authoritative.

New commitments (no adjacent mention AND not in the relation) flow through CREATE/LINK/SKIP.

### 6. Pre-match LINK candidates

For each `LINK`-classified commitment, find the best match in the `Current` view by Name + body keywords. Surface confidence inline. If a commitment plausibly matches no active task, demote to `DRAFT`.

### 7. Render plan to file, then request approval

**Always write the plan to a file before any approval prompt.** `AskUserQuestion` popups visually displace just-rendered chat text, so the plan must live on disk where the user can re-open and edit it.

1. Build the plan markdown (format below).
2. Write to `docs/tasks/_plan-YYYY-MM-DD-<meeting-slug>.md`. The `docs/tasks/` directory is already gitignored by `/setup-notion`, so the file stays local.
3. Print one line in chat referencing the file: `Plan written to [docs/tasks/_plan-YYYY-MM-DD-<meeting-slug>.md](...) — edit directly or reply approve / comment to iterate.`
4. Wait for the user's reply. **Do not call any approval popup** (no `ExitPlanMode`, no `AskUserQuestion` for approval). The user reads the file and replies in chat — that reply is the gate.

Plan format (single numbered list, summary line at top):

```markdown
# /create-tasks plan — <meeting title>

N items · X create · Y link · Z skip · W meeting-note annotations

## 1. <original commitment text>
**LINK** → [<task name>](<url>) · <Status> · @<assignee>
- Append to its `# Context`: topic section "<H2>" (NN lines · [expand])
- Annotate original text with inline mention-page in meeting body

## 2. <original commitment text>
**CREATE** · <Type> · <Complexity> · @<Display Name> (<member|guest> · <id-prefix>) · <Project or _unset_> · <Release> · Time: <YYYY-MM-DD or _unset_>
- Body: `# Context` + `## <meeting>` + topic section ([expand])
- Annotate original text with inline mention-page in meeting body

## 3. <commitment text>
**SKIP** — <one-line reason>

## ALREADY-LINKED (read-only, in meeting.Tasks already)
- [<task name>](<url>)
```

On iteration (step 8 comments), regenerate the plan markdown and **overwrite the same file** so the user always reads a current snapshot. Re-prompt by referencing the file path, not by re-rendering inline.

### 8. Iterate on free-form comments

Recognized recipes:

- `drop N` — remove item N from the plan.
- `merge A B` — combine items A and B into one row.
- `search deeper for N` — `notion-search` the full Roadmap for item N (widen beyond `Current`).
- `promote skip-N to draft` (or `to link`) — reclassify a skipped item.
- `change project to X for all` — bulk property edit on all CREATE rows.

Regenerate the plan markdown reflecting all comments in one revision. Re-enter plan mode.

### 9. Execute (only after plan-mode approval)

Order matters:

1. **Create new tasks.** `notion-create-pages` for each `CREATE`. Body shape — **prefix the content with a leading blank line** so the `# Context` H1 isn't the first block; otherwise Notion strips it as a duplicate-of-title at create time:
   ```markdown

   # Context

   ## <mention-page url="<source-url>"/>
   [bounding span pasted verbatim from the source content]
   ```
   The literal first character of the `content` string must be `\n`. A single leading newline (which renders as an empty paragraph in the block tree) is enough to protect the H1 — verified empirically. No fixup call is needed afterward.

   **Standalone variant**: omit the `## <mention-page .../>` line — `# Context` contains the bounding span only, with no source-page breadcrumb (there is none).
   Properties at creation:
   - `Type=` per the plan (see step 4 "Type classification"). `Task 🔨` only as fallback.
   - `Status=Not Started`
   - `Complexity=Moderate`
   - `Assignee=` only for assignees tagged `(member)`. **Omit Assignee on `(guest)` rows** — `create-pages` silently coerces guest IDs to the OAuth user. Handled in step 1b.
   - `Project=` inherited from the meeting's Project relation if present
   - `Release=` current quarter; fall back to most-recent existing option if the current quarter isn't in the enum (flag in plan)
   - `date:Time:start` = the date resolved in step 4 "Time extraction"; add `date:Time:end` only if step 4 captured a range.
   - Leave `Priority`, `Tags`, `Github Link` blank.

1b. **Fan out guest assignees.** For each created task whose resolved assignee is tagged `(guest)`, call `notion-update-page` `update_properties` to set `Assignee`. One call per affected task — `update_properties` accepts guest IDs reliably. Skip entirely when no `(guest)` assignees exist.

   **LINK appends** in step 9.2 below: the appended `## <mention-page url="<source-url>"/>` line uses the source URL (meeting / custom parent). Standalone has no LINK rows by construction (idempotency anchors are inactive → all commitments are CREATE/SKIP).

2. **Append to LINK targets.** For each LINK target URL:
   - Dispatch `/fetch-task <task-url>` to refresh `docs/tasks/<slug>.md`.
   - Build one `update_content` op: `old_str` = byte-exact last block under `# Context` (or the `# Context` heading itself if empty); `new_str` = same anchor + `\n\n## <mention-page url="<source-url>"/>\n[topic section verbatim]`.
   - If no `# Context` exists, anchor on top-of-body and insert a fresh `# Context\n\n## ...` block.
   - Call `notion-update-page` with `update_content`.

3. **Set the source page's `Tasks` relation.** `notion-update-page` `update_properties` with the relation extended to include all created + linked task IDs. Notion auto-mirrors the back-reference on the task side (we only write one side). **Skip entirely** when there is no source page (Standalone) or the source page has no `Tasks` relation property (custom-parent variant).

4. **Annotate the source page body.** Build one `notion-update-page` `update_content` call on the **source page** with N ops, one per processed commitment. **Skip entirely** when there is no source page (Standalone) or the source page has no `Tasks` relation property (custom-parent variant).
   - `old_str` = the exact commitment text captured in step 4 (byte-exact from the original body).
   - `new_str` = the **same commitment text followed by a `<mention-page url="<task-url>"/>` reference**, space-separated, inline. Preserves the original wording.

   The MCP enforces byte-exact matching. If any op fails (LLM paraphrased the text, body changed since fetch), the whole call fails — surface the failure, don't retry blind.

5. **Refresh the local mirror.** Meeting / treat-as-meeting only. `notion-fetch` the meeting page again and overwrite `docs/meetings/<YYYY-MM-DD>-<slug>.md` with the post-execution body + refresh `last_synced` to reflect the task links added in the body. **Skip** for Standalone and custom-parent variants (no mirror exists).

### 10. Post-create checkout picker

After successful execution, prompt via `AskUserQuestion` (multi-select):

- Question: "Check out which of these tasks locally?"
- Options: one per created + linked task (Name as label). Plus an explicit "None — done."

For each selected URL, dispatch `/fetch-task <url>`. Skipped silently if 0 tasks were affected this run (no checkout prompt at all).

`/create-tasks` itself never reads or writes `docs/tasks/<slug>.md` directly — all local-file logic lives in `/fetch-task`.

## Hard constraints (load-bearing)

- **No Notion writes before plan approval.** User's chat reply against the plan file (step 7) is the gate. Reads are fine.
- **Never call `ExitPlanMode`.** Popups displace plan text.
- **Body writes only inside `# Context`.** Never touch `# Description`, `# Updates`, `# Changes Made`, `# Result`, `# Release Notes`, `# Resource`, or legacy dated `# <mention-date>` blocks.
- **Never overwrite existing properties on existing tasks.** LINK targets only get `# Context` appends + relation inclusion.
- **Body content is the bounding topic section, verbatim.** No synthesis.
- **LINK appends go through `/fetch-task` first** for the byte-exact `# Context` anchor.
- **Meeting body annotates, doesn't replace.** `new_str` contains `old_str` as prefix.
- **Idempotency on re-run.** Anchors: meeting's `Tasks` relation; adjacent `<mention-page>` annotation.
- **Annotation pass runs only after Notion writes succeed.**
- **`create-pages` Assignee is best-effort for guests** — silently coerces to OAuth user. Omit on `(guest)` rows; set via `update_properties` post-create (step 9.1b).
- **Meeting properties never modified** (Date, Participants, Project — all untouched). Task-side `Discussions` relation auto-mirrors when we write meeting's `Tasks` — don't write both sides.
- **Source page is optional.** Three variants: (1) meeting / treat-as-meeting — full machinery; (2) custom parent — runs 9.3 + 9.4 only if parent has a `Tasks` relation; always skips 9.5 (no mirror); (3) Standalone — no source page, skips 9.3 + 9.4 + 9.5, `# Context` is span-only with no mention-page prefix. Variants (2)-without-relation and (3) disable all idempotency anchors — re-runs duplicate; the plan header must warn.
