---
name: upload-meeting
description: Upload a markdown meeting note to the configured Notion Meetings DB. Accepts a local .md file path, a Google Docs URL, or pasted markdown text. Prompts for Title / Date / Participants when missing, creates the page via `notion-create-pages`, and prints the new page URL. Body shape uses Notion's native `<meeting-notes>` block (with `<transcript>` populated when available) at the top, followed by the synthesized 整理過的會議記錄 as the page body. Transcript source priority: sibling `<basename>-transcript.*` sidecar (per `/meeting-notes` convention), then recent transcript-shaped paste in conversation history. After successful upload of a local file, annotates it with `notion.page` frontmatter for idempotency. If the input itself looks like a raw transcript rather than synthesized notes, recommends running `/meeting-notes` first. Use when the user says "/upload-meeting", "upload this meeting to Notion", "push meeting note to Notion", or when dispatched from `/meeting-notes` (post-save chain) or `/create-tasks` (non-Notion preflight, meetings-DB branch only).
---

# upload-meeting — meeting markdown → Notion Meetings DB

Authority: **Notion is master.** Writes one page to the configured Meetings DB. No custom parents, no standalone branch — those variants live in `/create-tasks`.

## 1. Resolve config

Read `AGENTS.md` (preferred) / `CLAUDE.md`. Locate the `## Notion` section. Extract **Meetings DB URL** and the optional `Meetings title format` line.

If the Meetings DB URL is missing → dispatch `/setup-notion`, then re-read `AGENTS.md` from scratch and continue. Do not assume setup succeeded — re-validate.

## 2. Resolve input

Three accepted shapes (priority order):

1. **Local `.md` / `.markdown` file path** → `Read` the file.
2. **Google Docs URL** → fetch via `WebFetch`. If auth-walled, ask the user to paste the contents.
3. **Pasted markdown text** — treat the most recent user message containing markdown-shaped text as the source.

If none of the above is present, ask via `AskUserQuestion`: paste markdown / local path / Google Docs URL.

**Idempotency check (local-file only).** If the file has `notion.page` frontmatter, `AskUserQuestion`: (1) Open existing page (recommended), (2) Upload as new page (§6 overwrites), (3) Cancel.

## 3. Transcript guard

Scan the resolved input for transcript markers (Speaker labels, recurring `HH:MM:SS`, raw dialog density, verbal cues). If the input looks like a dialog / transcript, `AskUserQuestion`: (1) Run `/meeting-notes` first (recommended) — dispatch, then re-enter §2 with the produced markdown, (2) Upload anyway, (3) Cancel.

## 4. Identify metadata

From the markdown body / filename:

- **Title** — first H1, or filename stem.
- **Date** — `YYYY-MM-DD` from (in order) filename pattern, `日期：…` line, today.
- **Participants** — `與會者：…` line or participants H2. Resolve each via `notion-get-users` (member) → `notion-search query_type=user` (guest); unmatched → plain-text fallback.

Compose the page title using AGENTS.md's `Meetings title format` (substitute `<date>` / `<topic>`; fall back to `<topic>` alone).

Confirm Title / Date / Participants via one `AskUserQuestion` round — skip only if all three are unambiguous.

## 5. Create the meeting page

One `notion-create-pages` call. 

### 5-1. Properties

**Fetch the Meetings DB schema first** (`notion-fetch` on the DB URL) — property names vary per workspace.

- **Parent** = Meetings DB
- **Title** = composed per §4
- **Properties** — map by type, name as tiebreaker; skip silently if a type isn't present:
  - **Date** → the `date`-typed property (tiebreaker: name closest to `date` / `日期` / `meeting date`).
  - **Participants** → the `people` / `person` (or attendees `relation`) property (tiebreaker: name closest to `participants` / `attendees` / `與會者`).

### 5-2. Transcript (if exists)

Look for a raw transcript independently of the notes source:

1. **Sidecar** (local-file only) — `<basename>-transcript.*` in the same directory (`/meeting-notes` §4 convention).
2. **Conversation history** — most recent user message with ≥2 of: speaker labels (`Speaker N` / `講者 N`), `HH:MM:SS` timestamps, dialog block >500 chars. Print `Using transcript from earlier paste (N lines).` so the user can correct.

If transcript is found, add Notion's native `<meeting-notes>` block, then synthesized notes below:

  ```
  <meeting-notes>
  <title-line: composed title from §4>
  <notes>
  </notes>
  <transcript>
  [raw transcript verbatim, from §2 resolution — empty if none]
  </transcript>
  </meeting-notes>
  ```
  `<notes>` stays empty by design — synthesized notes live below the block.

If no transcript is found, skip the `<meeting-notes>` block entirely and just put synthesized notes in the page body.

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
- **Transcript source is optional, resolved with explicit priority.** Sidecar file (local-file only) > recent conversation-history paste > none. When none, the `<meeting-notes>` block is still emitted with an empty `<transcript>` slot — preserves page shape and lets users paste a transcript later in Notion's native UI. Conversation-history match must be surfaced in chat so the user can correct a wrong paste before upload.
- **Body uses Notion's native `<meeting-notes>` block, not a generic toggle.** Shape verified via `notion-fetch` with `include_transcript: true`. The block carries the transcript only; synthesized notes go below it as the page's main body.
- **Property names are schema-driven, not hardcoded.** Always fetch the Meetings DB schema first and map metadata by property type (`date`, `people`/`person`/`relation`). Workspace variations (`日期` vs `Date`, `與會者` vs `Attendees`) must work without code changes.
