---
name: upload-meeting
description: Upload a markdown meeting note to the configured Notion Meetings DB. Accepts a local .md file path, a Google Docs URL, or pasted markdown text. Prompts for Title / Date / Participants when missing, creates the page via `notion-create-pages`, and prints the new page URL. Body is the synthesized 整理過的會議記錄, with the transcript (when available) in a collapsed 逐字稿 toggle at the end. Transcript source priority (see §4b): (1) `資料來源` / `Source` / `Transcript` reference in the meeting body, (2) sibling `<basename>-transcript.*` sidecar (per `/meeting-notes` convention), (3) recent conversation-history mention or paste, (4) explicit `AskUserQuestion` when ambiguous — never silently treat as "none." After successful upload of a local file, annotates it with `notion.page` frontmatter for idempotency. If the input itself looks like a raw transcript rather than synthesized notes, recommends running `/meeting-notes` first. Use when the user says "/upload-meeting", "upload this meeting to Notion", "push meeting note to Notion", or when dispatched from `/meeting-notes` (post-save chain) or `/create-tasks` (non-Notion preflight, meetings-DB branch only).
---

# upload-meeting — meeting markdown → Notion Meetings DB

Authority: **Notion is master.** Writes one page to the configured Meetings DB. No custom parents, no standalone branch — those variants live in `/create-tasks`.

## 1. Resolve config

Read `AGENTS.md` (preferred) / `CLAUDE.md`. Locate the `## Notion` section. Extract **Meetings DB URL** and the `Meetings title format` line.

If the Meetings DB URL is missing → dispatch `/setup-notion`, then re-read `AGENTS.md` from scratch and continue. Do not assume setup succeeded — re-validate.

If `Meetings title format` is missing → `AskUserQuestion` with common formats:
- `<date start="<date>" /> <topic>` (`<mention-date …/>` is saved as literal text; matches the `@今天 週會` template style — works for single dates and ranges via `start`/`end` attributes)
- `<topic>` alone (no date in title; date lives only in the date property)
- Custom (user provides their own template, using `<date>`, `<start>`, `<end>`, `<topic>` as substitution tokens)

Persist the chosen line under the `## Notion` section in AGENTS.md inline. One-shot — future runs in the same repo inherit. Treat a missing format like a missing DB URL: a config gap to resolve up-front, not a silent fallback later in §4.

## 2. Resolve input

Three accepted shapes (priority order):

1. **Local `.md` / `.markdown` file path** → `Read` the file.
2. **Google Docs URL** → fetch via `WebFetch`. If auth-walled, ask the user to paste the contents.
3. **Pasted markdown text** — treat the most recent user message containing markdown-shaped text as the source.

If none of the above is present, ask via `AskUserQuestion`: paste markdown / local path / Google Docs URL.

**Idempotency check (local-file only).** If the file has `notion.page` frontmatter, fetch that page, then `AskUserQuestion`:

- **Page lacks a 逐字稿 toggle AND §4b resolved a transcript** — offer (1) **Append transcript** (recommended; §5-2 toggle via `insert_content`), (2) Open existing page as-is, (3) Upload as new page (§6 overwrites), (4) Cancel.
- **Otherwise** — offer (1) Open existing page (recommended), (2) Upload as new page (§6 overwrites; re-wiring task cross-links is the caller's problem, e.g. `/create-tasks`), (3) Cancel.

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

**Local file + Notion token → script.** After §4 / §4b, run (`run_in_background`; the body and transcript never pass through you): `<dev-skills-root>/bin/notion-io.py upload-meeting <note.md> --db <Meetings DB URL> --title "<title>" --props '{"<date prop>": "YYYY-MM-DD", "<participants prop>": ["<uuid>", …], "<project prop>": ["<id>"]}' [--transcript <file>]`. The title may contain `<date start="YYYY-MM-DD" />`. Guests can go straight into people properties. It creates the page, writes the body, adds the 逐字稿 toggle, and writes §6's frontmatter. For an existing page missing the toggle, use `--page <url> --transcript <file>`. Exit 3 (no token) or pasted/Docs input → the MCP path below.

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

Notion's markdown spec makes the `<meeting-notes>` transcript section read-only — never add it to new pages. Instead, append the transcript **after** the synthesized notes as a collapsed toggle:

  ```
  <toggle heading="h2">
  逐字稿

  [raw transcript verbatim]
  </toggle>
  ```

Long transcripts: create the page with the notes first, then append the toggle via `notion-update-page` `insert_content` (position end). No transcript → omit the toggle.

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
- **Never write a `<meeting-notes>` transcript section.** The spec marks it read-only; the transcript goes in the §5-2 toggle at page end.
- **Property names are schema-driven, not hardcoded.** Always fetch the Meetings DB schema first and map metadata by property type (`date`, `people`/`person`/`relation`). Workspace variations (`日期` vs `Date`, `與會者` vs `Attendees`) must work without code changes.
- **MCP write responses echo input, not persisted state.** After `notion-create-pages`, `notion-fetch` the created page and spot-check: (1) the Date property (`is_datetime: 0` quirk — see §5-1), (2) body content for transcription errors, (3) Participants and Project relations. Treating the create response as proof-of-write has caused silent data corruption.
