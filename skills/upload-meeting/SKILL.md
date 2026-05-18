---
name: upload-meeting
description: Upload a markdown meeting note to the configured Notion Meetings DB. Accepts a local .md file path, a Google Docs URL, or pasted markdown text. Prompts for Title / Date / Participants when missing, creates the page via `notion-create-pages`, and prints the new page URL. Body shape uses Notion's native `<meeting-notes>` block (with `<transcript>` populated when available) at the top, followed by the synthesized 整理過的會議記錄 as the page body. Transcript source priority (see §4b): (1) `資料來源` / `Source` / `Transcript` reference in the meeting body, (2) sibling `<basename>-transcript.*` sidecar (per `/meeting-notes` convention), (3) recent conversation-history mention or paste, (4) explicit `AskUserQuestion` when ambiguous — never silently treat as "none." After successful upload of a local file, annotates it with `notion.page` frontmatter for idempotency. If the input itself looks like a raw transcript rather than synthesized notes, recommends running `/meeting-notes` first. Use when the user says "/upload-meeting", "upload this meeting to Notion", "push meeting note to Notion", or when dispatched from `/meeting-notes` (post-save chain) or `/create-tasks` (non-Notion preflight, meetings-DB branch only).
---

# upload-meeting — meeting markdown → Notion Meetings DB

Authority: **Notion is master.** Writes one page to the configured Meetings DB. No custom parents, no standalone branch — those variants live in `/create-tasks`.

## 1. Resolve config

Read `AGENTS.md` (preferred) / `CLAUDE.md`. Locate the `## Notion` section. Extract **Meetings DB URL** and the `Meetings title format` line.

If the Meetings DB URL is missing → dispatch `/setup-notion`, then re-read `AGENTS.md` from scratch and continue. Do not assume setup succeeded — re-validate.

If `Meetings title format` is missing → `AskUserQuestion` with common formats:
- `<mention-date start="<date>"/> <topic>` (matches the `@今天 週會` template style — works for single dates and ranges via `start`/`end` attributes)
- `<topic>` alone (no date in title; date lives only in the date property)
- Custom (user provides their own template, using `<date>`, `<start>`, `<end>`, `<topic>` as substitution tokens)

Persist the chosen line under the `## Notion` section in AGENTS.md inline. One-shot — future runs in the same repo inherit. Treat a missing format like a missing DB URL: a config gap to resolve up-front, not a silent fallback later in §4.

## 2. Resolve input

Three accepted shapes (priority order):

1. **Local `.md` / `.markdown` file path** → `Read` the file.
2. **Google Docs URL** → fetch via `WebFetch`. If auth-walled, ask the user to paste the contents.
3. **Pasted markdown text** — treat the most recent user message containing markdown-shaped text as the source.

If none of the above is present, ask via `AskUserQuestion`: paste markdown / local path / Google Docs URL.

**Idempotency check (local-file only).** If the file has `notion.page` frontmatter, fetch that page first to check whether it already has a `<meeting-notes>` block, then `AskUserQuestion` with the appropriate options:

- **Page has no `<meeting-notes>` block AND §4b resolved a transcript** — offer (1) **Retrofit transcript** (recommended; `update_content` inserts a fresh `<meeting-notes>` block — server allows this), (2) Open existing page as-is, (3) Upload as new page (§6 overwrites), (4) Cancel.
- **Page has an existing `<meeting-notes>` block** — `<transcript>` slot is server-locked (see Hard constraints). Offer (1) Open existing page (recommended), (2) Upload as new page (§6 overwrites; re-wiring task cross-links to the new URL is the caller's problem, e.g. `/create-tasks` annotations), (3) Cancel.
- **Page already has the transcript content matching the resolved one** — just open existing page.

## 3. Transcript guard

Scan the resolved input for transcript markers (Speaker labels, recurring `HH:MM:SS`, raw dialog density, verbal cues). If the input looks like a dialog / transcript, `AskUserQuestion`: (1) Run `/meeting-notes` first (recommended) — dispatch, then re-enter §2 with the produced markdown, (2) Upload anyway, (3) Cancel.

## 4. Identify metadata

From the markdown body / filename:

- **Title** — first H1, or filename stem.
- **Date** — `YYYY-MM-DD` from (in order) filename pattern, `日期：…` line, today.
- **Participants** — `與會者：…` line or participants H2. Resolve each name per **`/create-tasks` §4 "Assignee resolution"** strict ladder: (a) `### Team` roster in AGENTS.md → (b) `notion-get-users` (member) → (c) `notion-search query_type=user` for **EACH alias** in the doc (CJK name, romanized alias, surrounding email — search each separately, not as one combined query) → (d) `AskUserQuestion` for ambiguous. ALL steps mandatory before plain-text fallback. Eagerly append new (c)/(d) hits to `### Team` (not batched). Carry the `(member)` / `(guest)` tag through to §5-1.

Compose the page title using AGENTS.md's `Meetings title format` (substitute `<date>` / `<start>` / `<end>` / `<topic>` as the template specifies). §1 guarantees this line exists; if it's missing here, re-dispatch §1 — do not silently default.

Confirm Title / Date / Participants via one `AskUserQuestion` round — skip only if all three are unambiguous.

## 4b. Locate transcript source

Before composing the create-page call, resolve a transcript independently of the notes. Run the checks in order; stop at the first resolution:

1. **Body source reference** — scan the meeting body for `資料來源[:：]`, `Source:`, `Transcript:`, or similar source-attribution markers. If a filename is mentioned, look for it in the same directory as the meeting note (or paths relative to it). This is the primary signal for meetings produced by `/meeting-notes`.
2. **Sidecar file** (local-file input only) — explicitly `Bash ls <basename>-transcript.*` in the same directory. The skill MUST do this filesystem check; do not assume "no transcript" without it.
3. **Conversation history** — two sub-checks, both worth running:
   - **Mention** — earlier turns where the user referenced a transcript by path, filename, or URL (e.g. `"transcript is at ./foo-transcript.txt"`, `"see [pasted transcript above]"`, Google Drive / Plaud URL). Especially common when this skill is dispatched immediately after `/meeting-notes`, which produces the transcript path as part of its output.
   - **Paste** — most recent user message containing ≥2 of: speaker labels (`Speaker N` / `講者 N`), `HH:MM:SS` timestamps, dialog block >500 chars. Print `Using transcript from earlier paste (N lines).` so the user can correct.
4. **Ambiguous / not found** — `AskUserQuestion`: "Is there a transcript for this meeting?" Options: (a) Yes — paste path, (b) Yes — paste text, (c) No transcript. Do NOT silently assume "none."

The §5-2 block builder consumes the resolved transcript from this step. Do not re-do the lookup inside §5-2.

## 5. Create the meeting page

One `notion-create-pages` call. 

### 5-1. Properties

**Fetch the Meetings DB schema first** (`notion-fetch` on the DB URL) — property names vary per workspace.

- **Parent** = Meetings DB
- **Title** = composed per §4
- **Properties** — map by type, name as tiebreaker; skip silently if a type isn't present:
  - **Date** → the `date`-typed property (tiebreaker: name closest to `date` / `日期` / `meeting date`). **ALWAYS also send `date:<prop>:is_datetime: 0`** (integer literal `0`, not `__NO__`). Without it, Notion silently defaults the date to today, even though `create-pages` echoes the input back unchanged. After create, `notion-fetch` and spot-check the date.
  - **Participants** → the `people` / `person` (or attendees `relation`) property (tiebreaker: name closest to `participants` / `attendees` / `與會者`). **Set only `(member)` entries at create time** — `notion-create-pages` silently coerces guest IDs to the OAuth user (same gotcha as `/create-tasks` §9.1b Assignee). For each `(guest)` participant, run a follow-up `notion-update-page` `update_properties` to add them after create.
  - **Project** → `relation` property whose target data source's title or `name` contains `Project` / `專案`. Resolve by `notion-search query_type=internal data_source_url=<projects-collection>` using the meeting topic as the query:
    - **Exactly one match** → set it.
    - **Multiple matches** → `AskUserQuestion` with the top 3 (label = project name, description = first 80 chars of body).
    - **No match** → leave empty.
    Skip silently if no relation property's target looks Project-shaped. `/create-tasks` does NOT defensively fill this later — Project is owned by this skill alone.

### 5-2. Transcript block (when §4b resolved one)

If §4b resolved a transcript, add Notion's native `<meeting-notes>` block here, then synthesized notes below. Canonical syntax (verify against `notion://docs/enhanced-markdown-spec` via `ReadMcpResourceTool` if unsure):

  ```
  <meeting-notes>
  	<composed title as plain rich text — first child of meeting-notes>
  	<notes>
  	</notes>
  	<transcript>
  		[raw transcript verbatim, each line tab-indented one level deeper than <transcript>]
  	</transcript>
  </meeting-notes>
  ```

  Rules (each is load-bearing; getting any wrong silently drops content):
  - **Title is plain rich text**, not a `<title-line: …>` tag. The `<title-line:>` syntax does not exist — Notion stores it as escaped literal text and the parser bails on subsequent siblings, dropping `<transcript>`.
  - **All content inside `<notes>` / `<transcript>` must be tab-indented at least one level deeper than the parent tag** (Notion-flavored markdown requirement). Heading and bullet markers inside the slots still parse correctly when tab-indented.
  - **`<notes>` stays empty** by design — synthesized notes go below the block in the page body. Filling `<notes>` is technically allowed but breaks the convention with workspace pages that don't use `<meeting-notes>` at all.

If no transcript is found, skip the `<meeting-notes>` block entirely and just put synthesized notes in the page body. **Never emit an empty `<transcript>` slot hoping to fill it later** — see Hard constraint on transcript write-once below.

### 5-3. Body

**Synthesized notes body** — the markdown content verbatim. 
  ```
  [synthesized notes markdown verbatim — exact full structured 會議記錄 from /meeting-notes. ]
  ```

Print one line in chat: `Uploaded to Notion: <url>`.

## 6. Annotate local file (local-file input only)

After a successful upload, write/update frontmatter on the local input file linking it to the new Notion page:

```yaml
---
notion:
  page: <created-page-url>
  last_synced: <ISO-8601 timestamp>
---
```

Rules:

- **Has existing frontmatter** → merge under the `notion:` key only. Preserve every other frontmatter key byte-identical. Overwrite `notion.page` / `notion.last_synced` if they exist (re-upload path from §2).
- **No existing frontmatter** → prepend a fresh frontmatter block, followed by a blank line, before the first line of content.
- **Skip entirely** for Google Docs / pasted-text inputs — no file to annotate.

This mirrors `/fetch-task`'s `notion.page` convention. §2's idempotency check reads the same field, so re-runs are detected.

## Hard constraints

- **Only writes to the Meetings DB.** Custom-parent and standalone branches belong to `/create-tasks`; do not re-implement them here.
- **No body synthesis.** Markdown is uploaded verbatim — this skill does not rewrite, restructure, or summarize content.
- **Transcript guard runs before metadata extraction.** Don't prompt the user for Title/Date when the input shouldn't be uploaded as a meeting note in the first place.
- **Single page per invocation.** No batch upload — callers loop if they need multiple.
- **Local-file annotation is best-effort and idempotent.** Frontmatter is written only after a successful upload. Re-runs detect existing `notion.page` and prompt before creating a duplicate. Skip silently for non-file inputs.
- **Transcript source resolution lives in §4b.** Priority: (1) body source-reference line (`資料來源` / `Source` / `Transcript`) > (2) sidecar file `<basename>-transcript.*` > (3) conversation-history mention or paste > (4) explicit `AskUserQuestion`. Never silently default to "no transcript" — the user must confirm. Conversation-history match must be surfaced in chat so the user can correct a wrong paste before upload.
- **`<transcript>` is write-once per `<meeting-notes>` block.** Server rejects modifications to an **existing** `<transcript>` slot (`update_content` / `replace_content`) with `"Editing transcripts via AI is disabled to preserve the original conversation. Users can manually edit the transcript."` **However: inserting a brand-new `<meeting-notes>` block via `update_content` IS allowed** on pages that don't yet have one — verified empirically. Implication for §2 idempotency:
    - **Page without `<meeting-notes>` block** → late-arriving transcript can be retrofitted via `update_content` (prepend a fresh `<meeting-notes>` block).
    - **Page with existing `<meeting-notes>` block** → server-locked. Retrofit requires re-upload as a new page (manual UI edit is also possible inside Notion).
  Surface this distinction in §2's idempotency prompt when an existing page is detected and a transcript is now available.
- **Body uses Notion's native `<meeting-notes>` block, not a generic toggle.** Shape verified via `notion-fetch` with `include_transcript: true`. The block carries the transcript only; synthesized notes go below it as the page's main body.
- **Property names are schema-driven, not hardcoded.** Always fetch the Meetings DB schema first and map metadata by property type (`date`, `people`/`person`/`relation`). Workspace variations (`日期` vs `Date`, `與會者` vs `Attendees`) must work without code changes.
- **MCP write responses echo input, not persisted state.** After `notion-create-pages`, `notion-fetch` the created page and spot-check: (1) the Date property (`is_datetime: 0` quirk — see §5-1), (2) body content for transcription errors, (3) Participants and Project relations. Treating the create response as proof-of-write has caused silent data corruption.
