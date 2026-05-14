---
name: fetch-task
description: Pull a Notion task into a local working file at docs/tasks/<slug>.md. Creates the file on first run; on subsequent runs, refreshes only the managed `# Context` section + frontmatter `last_synced` while preserving every other section byte-identical. With no args, shows a picker of the current user's active tasks (Current view, Assignee == me). Use when the user says "/fetch-task", "fetch task", "check out this Notion task", or passes a Notion task URL.
---

# fetch-task — Notion task → local working file

Authority: Notion is master. **This skill is read-only against Notion.** Never calls `notion-create-pages`, `notion-update-page`, or any write tool.

## Inputs

- `/fetch-task <url>` → fetch that one task.
- `/fetch-task` (no arg) → picker of the current user's active tasks.
- Called from another skill (e.g. `/create-tasks` post-create checkout) with one or more URLs → operate on those, no picker.

## Flow

### 1. Resolve config

Read `AGENTS.md` (preferred) / `CLAUDE.md`. Locate the `## Notion` section. Need at least the Roadmap DB URL (for the picker) — Meetings URL is not used here.

If config is missing → dispatch `/setup-notion`, then re-read and continue.

### 2. Resolve targets

**One URL passed in** → skip picker, single-target fetch.

**Multiple URLs passed in (called from another skill)** → multi-target fetch, no picker, no per-URL prompts.

**No arg** → picker flow:

- Resolve "me": read `~/.claude/memory/notion-me.md`. If missing or empty, prompt once via `AskUserQuestion`:
  - Question: "Who are you in Notion? (used to filter your active tasks)"
  - Options: top ~5 candidates from `notion-search` on workspace users by name/email if available, plus a "Paste user ID" escape hatch.
  - On selection, write the resolved Notion user ID to `~/.claude/memory/notion-me.md`. **Do not** write the per-dev ID into `AGENTS.md`.
- Query the Roadmap data source's `Current` view (by name; fall back to first non-Completed view) filtered by `Assignee == me`.
- Present results via `AskUserQuestion` (multi-select):
  - Columns: Name · Status · Project · Time
  - Plus a "Paste URL" escape hatch and "Cancel".
- Selected URLs flow into the per-URL loop below.

### 3. For each URL

#### 3a. Fetch

`notion-fetch` the task page. Capture body markdown, Name, Status, current property values.

#### 3b. Compute local path

`docs/tasks/<slug>.md` where:
- `<slug>` = task Name, lowercased, path-unsafe chars replaced with `-`, collapsed runs of `-`, truncated to ~60 chars.
- Appended with `-<hash6>` where `<hash6>` is the first 6 hex chars of the Notion page ID (UUID's hyphens stripped). This protects against name collisions and rename-after-fetch.
- Create `docs/tasks/` directory if missing.

#### 3c. Write or refresh

**File doesn't exist (first fetch)** → write the full file:

```markdown
---
notion:
  page: <task-url>
  last_synced: <ISO-8601 timestamp>
---

<!-- synced from Notion by /fetch-task · do not edit # Context locally; edits will be lost on refresh -->
# Context

## <mention-page url="<meeting-url>"/>
[topic section content from the Notion task]

## <mention-page url="<another-meeting-url>"/>
[next topic section]
```

If the Notion task body has **no `# Context` heading** (older task, or one created ad-hoc via `/sync-report`'s create-new branch), the local file gets a placeholder:

```markdown
# Context

_(This Notion task has no managed `# Context` section. Add working notes below under your own headings.)_
```

**File exists (refresh mode)** → in-place edit:
- Replace **only the `# Context` block** (from the `# Context` heading up to but not including the next `# `-level heading, or EOF) with the fresh content from Notion.
- Update `notion.last_synced` in frontmatter.
- Every other section is byte-identical before/after. `# Notes`, `# Plan`, `# Scratch`, anything the dev wrote outside `# Context` — untouched.
- Frontmatter `notion.page` is **immutable** once set. Refreshes never rewrite it.
- The managed-marker comment is preserved if present; not re-inserted if a dev deleted it.

If the Notion task has no `# Context` section but the local file already has the placeholder, leave the placeholder in place (don't re-insert; don't replace with empty).

#### 3d. Terminal-status prompt

If the task's current Status is `Completed 🙌` or `Paused`, fire `AskUserQuestion` **every refresh** (no transition tracking — current state alone triggers):

- Question: `Notion task is <Status> — what now?`
- Options:
  - `Keep working` — continue, no further action.
  - `Archive locally` — move the file to `docs/tasks/archive/<slug>.md` and exit this URL's loop (create `docs/tasks/archive/` if missing).
  - `Run /report` — dispatch `/report` on this file.
  - `Cancel` — abort this URL's fetch (file already written / refreshed at this point; "cancel" only stops the post-fetch action).

### 4. Summary

Print one line per URL processed: `<path> · <action: created|refreshed|archived>`.

## Hard constraints

- **Read-only against Notion.** Never calls a Notion write tool.
- **Local writes only inside `# Context` and frontmatter.** Every other section is byte-identical before/after refresh.
- **`# Context` is unconditionally overwritten on refresh.** No diff prompt, no merge. The managed-marker comment documents the convention.
- **Frontmatter `notion.page` is immutable** once set.
- **Picker source is the `Current` view filtered by `Assignee == me`** — not a whole-Roadmap search.
- **No file deletions.** If the upstream task is 404 (deleted/archived), surface options to the user (re-link / orphan / delete manually). Never auto-delete.
- **Per-dev "Me" ID lives in `~/.claude/memory/notion-me.md`.** Never in `AGENTS.md`.

## 404 handling

If `notion-fetch` returns 404 on a URL that was previously synced:

- Surface the error with the local file path.
- `AskUserQuestion` options:
  - `Re-link to a different task` — prompt for new URL, rewrite frontmatter `notion.page`.
  - `Treat as orphaned` — strip the frontmatter `notion.page` line, leave file in place.
  - `Delete manually later` — exit without changes.

Never auto-delete the local file.
