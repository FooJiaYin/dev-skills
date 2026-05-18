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

**Pre-flight idempotency check (local-file input only).** If the input is a local `.md` file, peek at its YAML frontmatter for `notion.page`. If present and the URL points at a Notion page (typically the Meetings DB, written by `/upload-meeting`), treat the input as if the user had passed that URL directly — skip the rest of the preflight and jump to §3 with that URL as the meeting page. This is the matching half of `/upload-meeting`'s annotation step: files already uploaded are recognized and not re-uploaded.

**Transcript guard.** Scan the input for transcript markers — speaker labels (`Speaker N`, `講者 N`), recurring `HH:MM:SS` timestamps, raw dialog density (sequences of short paragraphs without H2 structure). If **≥2** markers present, prompt via `AskUserQuestion`:

- Question: "This looks like a raw transcript, not meeting notes. Run `/meeting-notes` first?"
- Options:
  1. **Run `/meeting-notes` first** (recommended) — dispatch `/meeting-notes` with the current input. Re-enter this preflight with the produced markdown path.
  2. **Continue anyway** — proceed to the meeting-shape heuristic below.
  3. **Cancel** — abort.

Meeting-shape heuristic: input is meeting-shaped if ≥2 of {date marker like `2026-` / `日期:` / `## N月`, participant cluster, H2 section structure, length >~30 lines}.

- **Meeting-shaped** → dispatch `/upload-meeting` with the input. Read the returned page URL from chat (`Uploaded to Notion: <url>`). Continue with that as the meeting URL.
- **Not meeting-shaped** → `AskUserQuestion` 4-way picker:
  1. **Treat as meeting anyway** → dispatch `/upload-meeting` (same as meeting-shaped path).
  2. **Standalone tasks** → no source page. Skip steps 9.3, 9.4, 9.5. Each task's `# Context` is the bounding span only (no mention-page prefix). All idempotency anchors inactive — re-runs duplicate; the plan header warns.
  3. **Upload to custom parent** → prompt for a Notion parent page/DB URL. `notion-create-pages` as a child there. The new page URL is the source URL for every task's `# Context` mention-page prefix. If the parent has a `Tasks` relation property → run 9.3 + 9.4 against it. If not → skip 9.3 + 9.4; the per-task mention-page in `# Context` is the only breadcrumb, and idempotency anchors are inactive. Always skip 9.5 (no local mirror for custom parents).
  4. **Cancel** → abort.

From this point, operate on the resolved source page — or, for the Standalone branch, on the raw input text with no source page.

Meetings-DB title format is owned by `/upload-meeting` (it reads AGENTS.md's `Meetings title format` and applies it). Custom-parent uploads (handled inline here) use the first H1 / filename verbatim as the title.

### 3. Fetch meeting + active task pool

In parallel:
- `notion-fetch` the meeting page → body markdown, Participants, Project relation, **existing `Tasks` relation list** (for idempotency).
- `notion-fetch` the Roadmap data source → **schema** (property names + types) AND query the `Current` view by name (exact match; fall back to the first non-Completed view). Collect the ~10–30 active task rows: Name, Status, Assignee, Type, Project, first ~200 chars of body.

**Fan-out reads (when ≥2 non-Notion source files exist — e.g. local sheet export, sibling chat-export `.txt`).** Spawn a single Explore subagent with a tight prompt:
> Read the following sources verbatim and return a structured digest: <list of paths/URLs>. For each, list H2/H3 sections with line ranges, named participants, dated commitments, and any reference URLs. Return JSON; ≤500 lines per source summary.

The main thread continues from the digest instead of re-reading each source. Saves ~30s per large source on serial reads.

**Schema cache.** After fetching the Roadmap schema, write a compact map (property name → type → option list for selects) into the plan file (rendered in §7) under an HTML comment block:
```html
<!-- schema-cache
Name: title
Type: select(Feature ⛰️|Task 🔨|Bug 🐞|Survey 🔍|Test 🧪|Documentation 📄|Request)
Status: status(Not Started|Design|In Progress|...|Completed 🙌|Paused)
Complexity: number
Assignee: person
Project: relation→<projects-collection>
Time: date
…
-->
```
§9.1 reads from this block instead of re-fetching the schema, saving one round-trip on the execute pass.

**Reconcile schema.** Build a property-type map for every property §9.1 writes (Name, Type, Status, Complexity, Assignee, Project, Release, Time, Priority, Tags, Github Link). For each mismatch:
- **Property missing entirely** (e.g. no `Release` field) → skip that property at create-time; surface in the plan header.
- **Property type differs from §9.1's default expectation** (e.g. `Complexity` is `number` not text in this workspace) → translate the default per §9.1's "if schema supports it" rules; surface in plan header.

The plan header rendered in §7 MUST disclaim each adjustment so the user sees the deviation before approving.

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
  - The **proposed task name** — a short, verb-led restatement (~6–14 字 CJK / ~50 chars EN). Distinct from the verbatim span. CREATE rows use this as Notion's Name property; the verbatim span stays in the body as the annotation anchor. Strip parentheticals, attendee call-outs (e.g. "被 X 當人質監督"), and bullet-deadline suffixes when shortening.
  - **Related sections** (plural) — the H2/H3 sections in the source meeting body that semantically relate to this commitment. Scan the FULL source body for sections referencing the commitment's key tags:
    - Task name keywords (e.g. `訂金`, `v1.0`, `Straumann`, `翻譯`)
    - Date or version anchor (e.g. `5/9`, `v1.0`, `5/16`)
    - Assignee or counterparty names mentioned in the commitment
    - Deliverable type (e.g. `付款`, `設計`, `規劃書`)

    Capture the byte-range of each related section. A single commitment commonly maps to **2–4 sections** (one near the Action Items, others in the discussion body, possibly one in 結論 / 截止期程). Include all of them. The "bounding section the commitment text physically lives under" is usually just `## Action Items` and is the LEAST informative — explicitly EXCLUDE it unless no other section matches.
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

For each name, run ALL steps below in order. Plain-text fallback only after step (d) returns no resolution. Each source determines the `(member)` / `(guest)` tag carried through to step 9 (controls create-pages vs post-create update fan-out).

(a) **`### Team` roster in AGENTS.md** — exact match. Tag from the roster line. No remote call. If hit, stop here.
(b) **`notion-get-users`** — name OR email match → `(member)`.
(c) **`notion-search` `query_type=user`** — search **EACH alias** the doc body provides for the same person, separately:
   - CJK display name (e.g. `嘉尹`)
   - Romanized / English alias (e.g. `Foo Jia Yin`)
   - Any email visible in surrounding context
   - Any nickname / handle (e.g. `Dream One`)
   A single CJK-only search will MISS English-named guest accounts and vice versa. Match by name OR email → `(guest)`.
(d) **`AskUserQuestion`** — present the unresolved name with all aliases tried. Offer: paste email/ID, leave as plain-text, skip.

Plain-text in the page body is the fallback only after (d). Do not skip (b)/(c) because (a) was empty.

**Update roster.** On each new confirmation (via c) or (d), append to `### Team` immediately:

```
- <Display Name> <email@example.com> — <notion-user-id> (member|guest)
```

Eager — not batched. Later participants in the same run benefit (and future sessions hit (a)).

**Backfill missing `(member|guest)` tags.** Before appending new entries, scan existing `### Team` lines. If any predate the `(member|guest)` convention (no tag), surface ONCE via `AskUserQuestion`: "Roster has N untagged entries. Backfill now? (a) Yes — I'll classify each via `notion-get-users`/`notion-search`, (b) Leave as-is, (c) Default all to `(member)`." Then either backfill all in one edit or leave the inconsistency noted. Avoids silent format drift between old and new entries.

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

## 2. <proposed task name>
**CREATE** · <Type> · <Complexity> · @<Display Name> (<member|guest> · <id-prefix>) · <Project or _unset_> · <Release> · Time: <YYYY-MM-DD or _unset_>
- Source commitment: "<verbatim span — byte-exact, becomes the annotation anchor>"
- Body: `# Context` + `## <meeting>` + topic section ([expand])
- Annotate original text with inline mention-page in meeting body

## 3. <verbatim commitment text>
**SKIP** — <one-line reason>

## ALREADY-LINKED (read-only, in meeting.Tasks already)
- [<task name>](<url>)
```

**Body preview in the plan.** The `- Body:` line in each CREATE row should show the **first ~10 lines of each related section verbatim**, separated by `---`, so the user can sanity-check content before approval. For large batches (`N ≥ 10` CREATE rows), only materialize the full preview for the **first 3 tasks per Type group** (Feature / Survey / Documentation / Test / Task / Bug / Request) — remaining rows show a one-line `- Body: [related sections §<refs> — template applied]` summary. Saves ~10KB plan output on a 23-task batch.

**Schema cache.** Prepend the schema-cache HTML comment block (built in §3) right after the summary line, before the first row. §9.1 reads from it instead of re-fetching schema.

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

**Parallel body construction (when N ≥ 10 CREATE rows).** Many bodies were left as one-line summaries in the plan per §7 lazy preview. Before firing `notion-create-pages` in §9.1, materialize them: split CREATE rows into ~2 chunks by index and spawn 2 Plan subagents in parallel, each receiving its chunk + the meeting body + the body template from §9.1. Each agent returns `{ task_index, body_markdown }[]`. Main thread merges in order. For `N < 10`, the main thread materializes inline — fan-out overhead exceeds savings.

**Batch size for `notion-create-pages`.** If `N ≤ 50` CREATE rows, send one call. If `N > 50`, split into batches of ≤50 and send in parallel (same parent in each batch); collect task URLs from all responses before §9.1b.

Order matters:

1. **Create new tasks.** `notion-create-pages` for each `CREATE`. Body shape — **prefix the content with a leading blank line** so the `# Context` H1 isn't the first block; otherwise Notion strips it as a duplicate-of-title at create time:
   ```markdown

   # Context

   ## <mention-page url="<source-url>"/>

   ### 會議記錄 §<related sections, comma-separated>
   [verbatim content from each related section per §4 "Related sections", concatenated in document order, separated by `---` between sections]
   ```
   The literal first character of the `content` string must be `\n`. A single leading newline (which renders as an empty paragraph in the block tree) is enough to protect the H1 — verified empirically. No fixup call is needed afterward.

   **Opt-in transcript enrichment**: when the user explicitly asks to include a transcript / chat-export sidecar (do not auto-detect), append after the `### 會議記錄` block:
   ```markdown
   ### <Transcript label> <date range>
   **<time> <speaker>** <message verbatim>
   …
   ```
   Default is OFF — adding transcript fragments without explicit user instruction is over-reach.

   **Standalone variant**: omit the `## <mention-page .../>` line — `# Context` contains the related sections only, with no source-page breadcrumb (there is none).
   Properties at creation (apply only if the Roadmap schema supports each — see §3 "Reconcile schema". Skip silently for properties absent from the schema and surface the skip in the plan header):
   - `Name=` the plan's **proposed task name** (short verb-led restatement), NOT the verbatim commitment text. The verbatim text lives in the `# Context` body as the annotation anchor.
   - `Type=` per the plan (see step 4 "Type classification"). Default `Task 🔨` only as fallback. If schema options differ (e.g. `Survey 🔍` vs `Survey 🔎`), use the exact option name from the fetched schema.
   - `Status=Not Started` (or whatever the schema's "to-do" group's first option is named).
   - `Complexity` — `Moderate` if the property is text type; `3` if numeric; skip if absent.
   - `Assignee=` only for assignees tagged `(member)`. **Omit Assignee on `(guest)` rows** — `create-pages` silently coerces guest IDs to the OAuth user. Handled in step 1b. **Person property write format: JSON array of bare UUID strings** (e.g. `["<uuid>", "<uuid>"]`) — never `<mention-user>` tags (those are read-only).
   - `Project=` inherited from the meeting's Project relation if present.
   - `Release=` current quarter; fall back to most-recent existing option if the current quarter isn't in the enum; skip if absent (flag in plan).
   - `date:Time:start` = the date resolved in step 4 "Time extraction"; add `date:Time:end` only if step 4 captured a range. **ALWAYS also send `date:Time:is_datetime: 0`** (integer literal `0`, not the `__NO__` checkbox sentinel — that errors with "must be a number (0/1)"). Without it, Notion silently defaults the date to today, even though `create-pages` echoes the input back unchanged. **After the batch, `notion-fetch` one page and spot-check the date** — the create response is not authoritative for date properties.
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
- **Body content is the related sections, verbatim.** All related sections per §4 "Related sections", concatenated in document order. No synthesis — every line must originate verbatim in the source. Transcript fragments are off by default; only included when the user explicitly asks.
- **LINK appends go through `/fetch-task` first** for the byte-exact `# Context` anchor.
- **Meeting body annotates, doesn't replace.** `new_str` contains `old_str` as prefix.
- **Idempotency on re-run.** Anchors: meeting's `Tasks` relation; adjacent `<mention-page>` annotation.
- **MCP write responses echo input, not persisted state.** After any batch `notion-create-pages` or large `update-page`, `notion-fetch` at least one affected page and spot-check: (1) date properties (see is_datetime quirk in §9.1), (2) body content for transcription errors, (3) relation properties (especially person/people for guests). Treating the create response as proof-of-write has caused silent data corruption in this skill's history.
- **Annotation pass runs only after Notion writes succeed.**
- **`create-pages` Assignee is best-effort for guests** — silently coerces to OAuth user. Omit on `(guest)` rows; set via `update_properties` post-create (step 9.1b).
- **Meeting properties never modified** (Date, Participants, Project — all untouched). Task-side `Discussions` relation auto-mirrors when we write meeting's `Tasks` — don't write both sides.
- **Source page is optional.** Three variants: (1) meeting / treat-as-meeting — full machinery; (2) custom parent — runs 9.3 + 9.4 only if parent has a `Tasks` relation; always skips 9.5 (no mirror); (3) Standalone — no source page, skips 9.3 + 9.4 + 9.5, `# Context` is span-only with no mention-page prefix. Variants (2)-without-relation and (3) disable all idempotency anchors — re-runs duplicate; the plan header must warn.
