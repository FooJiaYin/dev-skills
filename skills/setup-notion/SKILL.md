---
name: setup-notion
description: One-time setup wizard that records org-shared Notion config (Roadmap DB URL, Meetings DB URL, optional team roster) in AGENTS.md and adds docs/tasks/ to .gitignore. Use when the user says "/setup-notion", "set up Notion config", "configure Notion for this repo", or when /create-tasks, /fetch-task, or /sync-report dispatches setup because AGENTS.md is missing a Notion section.
---

# setup-notion — shared Notion config wizard

Dispatched by `/create-tasks`, `/fetch-task`, and `/sync-report` when `AGENTS.md`'s `## Notion` section is missing or incomplete. Also runnable standalone. **Idempotent** — re-running on a fully-configured repo is a silent no-op.

Per-dev "Me" identity is **not** handled here — that lives in `~/.claude/memory/notion-me.md`, populated lazily by `/fetch-task` on first no-arg picker.

## Flow

### 1. Diagnose current state

Read `AGENTS.md` (preferred) or `CLAUDE.md` in CWD. Look for a `## Notion` section. Extract:

- **Roadmap DB URL** — line like `Roadmap (tasks): https://www.notion.so/...` or any `notion.so/<id>` URL near the word "roadmap" / "tasks".
- **Meetings DB URL** — line like `Meetings: https://www.notion.so/...` or any `notion.so/<id>` URL near "meeting".
- **Meetings title format** (optional) — a line like `Meetings title format: ...` near the Meetings URL.
- **Team roster** (optional) — a `### Team` subsection with markdown list items.

Read `.gitignore`. Determine whether `docs/tasks/` is covered (literal `docs/tasks/`, `docs/tasks`, or a broader pattern like `docs/`).

### 2. Skip if complete

If **Roadmap + Meetings DB URLs are both present** AND `.gitignore` covers `docs/tasks/`, print one line:

```
Notion is already set up — nothing to do.
```

…and exit. Dispatching skills can call `/setup-notion` unconditionally.

### 3. Prompt only for missing fields

Use `AskUserQuestion` for each missing field. Don't batch all prompts into one call — validate each URL before accepting the next.

**Roadmap DB URL** (if missing):
- Question: "Notion DB URL for the Roadmap / tasks database?"
- Options: paste-URL escape hatch only (no preset options).
- Validate by calling `notion-fetch` on the URL. If fetch fails or the returned object is not a database / data source, surface the error and re-prompt. Do not partially write.

**Meetings DB URL** (if missing):
- Same flow as Roadmap. Always collect, even if the dispatching skill is `/sync-report` or `/fetch-task` (cheap, the dev will likely need it later).

**Meetings title format** (if missing, and Meetings URL is set):
- Query the ~5 most recent rows from the Meetings data source. Derive a `<date> <sep> <topic>` pattern guess.
- Prompt with the 5 raw titles + derived pattern as the recommended option. Accept free-form override. Must contain `<date>` and `<topic>` placeholders.
- Skip the prompt if the DB has <2 rows; default to `<topic>`.

**Team roster** (always optional, single prompt):
- Question: "Paste the team roster, or skip."
- Show the expected format inline:
  ```
  - Alice <alice@gmail.com> — notion-user-id-1
  - David <david@gmail.com> — notion-user-id-2
  ```
- Options: `Skip`, `Paste`.
- On paste, validate each line has at least a name and a Notion user ID. No further checks. Reject malformed lines with a re-prompt.

### 4. Write to disk

**`AGENTS.md`:**
- If `AGENTS.md` exists, locate the `## Notion` section and update it in place with minimal edits (preserve any existing content; only insert/replace the specific missing lines). If there's no `## Notion` section, append one at the end of the file.
- If only `CLAUDE.md` exists, create `AGENTS.md`, copy its content, then `ln -sf AGENTS.md CLAUDE.md` (per the global convention). Subsequent writes go to `AGENTS.md`.
- If neither exists, create `AGENTS.md` with just the `## Notion` section.

Canonical section shape (insert verbatim; team roster only when collected):

```markdown
## Notion

Roadmap (tasks): <roadmap-url>
Meetings: <meetings-url>
Meetings title format: <MM月DD日> | <topic>

### Team

- Alice <alice@gmail.com> — notion-user-id-1 (member)
- David <david@gmail.com> — notion-user-id-2 (guest)
```

**`.gitignore`:**
- If `docs/tasks/` is not covered, append a line `docs/tasks/`. If `.gitignore` doesn't exist, create it with that one line.
- Detect broader patterns (`docs/`, `docs/tasks`, `**/tasks/`) and skip silently if matched.

### 5. Summary

Print a short summary of what changed:

```
Wrote AGENTS.md ## Notion section (Roadmap, Meetings, Team).
Appended docs/tasks/ to .gitignore.
```

Do **not** commit. The dispatching skill or the user decides when to commit setup changes.

## Hard constraints

- **Idempotent.** Re-running on a fully-configured repo exits at step 2.
- **Validate URLs before writing.** A bad DB URL never reaches disk. `notion-fetch` must return a database / data source object.
- **Per-dev "Me" never touches AGENTS.md.** That lives in `~/.claude/memory/notion-me.md`, written by `/fetch-task`.
- **Never commits.** Setup writes are staged for the user / dispatching skill.
- **Minimal edits to AGENTS.md.** Don't reformat unrelated sections. If `## Notion` exists with partial content, patch in place.
- **Fire-and-forget dispatch.** Calling skills invoke `/setup-notion`, then re-read AGENTS.md from scratch on return. They never pass state in or read state from the wizard.

## Notes for dispatchers

After dispatching `/setup-notion`, callers should:

1. Re-read `AGENTS.md` (or `CLAUDE.md` fallback) from disk.
2. Re-parse the `## Notion` section.
3. Continue their own flow.

Never assume the wizard succeeded — re-read and re-validate.
