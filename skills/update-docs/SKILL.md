---
name: update-docs
description: Detection-driven docs updater. Scans the project's doc layout, classifies the diff (schema / api / service / component / design / infra), proposes a per-file update plan, and edits only after user confirmation. Use when the user says "update the docs", "sync docs", "are the docs up to date?", "audit doc drift", or invokes /update-docs. Also invoked by /wrap-up step 3.
argument-hint: "[scope: default=uncommitted | <commit> | <range> | --pr <num> | --all]"
---

# update-docs — detection-driven docs updater

Update the project's documentation to match a code change. The skill adapts to whatever doc layout the project actually uses; it does not assume a single convention.

## 1. Resolve scope

Parse the argument (or default):

- **No arg / default** — current uncommitted diff (`git diff` + `git diff --staged` + new untracked files).
- **A commit SHA or `HEAD`** — `git show <sha>`.
- **A range** like `HEAD~3..HEAD` — `git diff <range>`.
- **`--pr <num>`** — fetch with `gh pr diff <num>`.
- **`--all`** — audit-mode: walk the whole repo, looking for code/doc drift rather than per-diff updates.

## 2. Detect doc layout

One fast scan; build a map of what doc files/folders exist:

- Top-level files: `README.md`, `AGENTS.md`, `CLAUDE.md`, `ARCHITECTURE.md`, `architecture.md`.
- Doc folders: `docs/`, `doc/`, `documentation/`.
- Inside each doc folder, look for:
  - `schemas/` (per-entity) vs `schema.md` (monolithic)
  - `api/` (per-resource) vs `api.md` (monolithic)
  - `components/` vs `components.md`
  - `design.md`, `services/`, `modules/`
  - `index.md` files (ERD overview, endpoint table, etc.)
- Per-repo splits: `backend/`, `frontend/`, `server/`, `client/`, `web/`, `mobile/`, `apps/*`, `packages/*`. For each subfolder that exists, repeat the doc scan inside it.

Classify each concern's convention as: **per-entity / monolithic / absent**.

## 3. Classify the diff

Read the scoped diff. Tag each change as one or more of:

- **schema** — DB models, ORM definitions, migration files, schema-shaped TypeScript types.
- **api** — route/handler/controller files, OpenAPI specs.
- **service / module** — service-layer or cross-cutting business logic.
- **component** — UI components, pages, layouts.
- **design-token** — CSS variables, theme files, Tailwind config, design system primitives.
- **infra** — Dockerfiles, CI configs, deploy scripts, folder-structure changes.

## 4. Propose

Print a single proposal showing both the detected layout and the file-by-file update plan, then **wait for user confirmation**:

```
Detected docs layout:
  schemas/  → per-entity (4 files)
  api.md    → monolithic
  no frontend docs folder

Proposed updates:
  schemas/user.md   + field `verified_at` (timestamp, nullable)
  schemas/index.md  update User entity row
  api.md            + section "POST /verify"

Confirm? [y/n/edit]
```

- Showing the detected layout lets the user catch mis-detection (e.g., a legacy `schema.md` left over from an in-progress migration).
- For ambiguous diffs (multiple plausible targets), list all and let the user pick.
- If no convention is detected for a concern, propose a sensible default (e.g., `docs/schema.md`) and **flag it** so the user can decide whether to adopt a structure.

## 5. Edit on confirmation

After the user confirms, apply the changes:

- Keep entries terse:
  - **Schemas**: fields, constraints, lifecycle. Not prose.
  - **APIs**: method, path, auth, request shape, response shape.
  - **Components**: prop signature, slot/composition pattern, where it's used.
- Always update the matching `index.md` (ERD entry, endpoint table row, component list) alongside any per-entity / per-resource change.
- If unrelated drift is noticed in the same file, **flag it but don't fix it inline** — surface as a follow-up at the end.
- Per global rule: prefer `AGENTS.md` over `CLAUDE.md`; prefer the `docs/` folder over scattered top-level files.

## Guardrails

- **Never edit before user confirmation.**
- Never delete doc files; only add or modify.
- If `--all` audit mode finds drift but the diff is empty, still go through Propose → Confirm before editing.
- If multiple repos are detected (e.g., `backend-repo/` and `frontend-repo/` as siblings), make it clear in the proposal which repo each file lives in.
