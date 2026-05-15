---
name: spec
description: |
  Generate a multi-file engineering specification from a system description or requirements.
  Use when the user says "spec", "generate a specification", "write a spec", "engineer spec",
  or wants to plan a new system's architecture, data models, APIs, and features before coding.
---

# Spec Skill

Generate a complete, multi-file engineering specification for a described system. Each file has one audience and one reason to change.

## Workflow

### Phase 1: Keyword Extraction

Silently scan the user's input for:

- **Domain keywords** — nouns that become entities (user, order, invoice)
- **Action keywords** — verbs that become features/flows (register, checkout, approve)
- **Tech keywords** — named technologies (React, PostgreSQL, Redis)
- **Constraint keywords** — NFRs or limits (real-time, offline-first, HIPAA)

Use these to seed clarification questions and pre-name feature files.

### Phase 2: Clarify First

Ask the user **at most 5 questions** — only for fields not inferable from the input. Each question must include a **Recommended:** line with your best-guess default.

Candidate questions (skip any already answered):

1. Stack choice — if no tech keywords detected
2. Audience depth — engineer-ready (default) vs. stakeholder-overview
3. Output directory — default `docs/spec/`
4. Key feature flows to cover — so `features/*.md` can be pre-named
5. Any known constraints or integrations

If the user answers "yes" or accepts, record the **Recommended** value.

### Phase 3: Generate Files

Write all files into the target directory (default `docs/spec/`). See **Output Structure** and **Per-File Content Rules** below.

### Phase 4: Cross-Link

- `specification.md` links to every sibling file via an index table
- Every file links back to `specification.md`
- `features/*.md` link into `api.md`, `frontend.md`, `schemas.md` where relevant
- All links are relative paths

### Phase 5: Self-Review

Before finishing, run an internal review pass:

- For each entity: check create / update / delete / archive / expire / transfer scenarios
- For each feature flow: check error, empty, loading, boundary cases
- If a scenario is obviously missing and safe to assume → add it with `[Added]` tag
- If ambiguous → add a `❓ Question` bullet and ask the user

### Phase 6: Report

Print the file tree that was created, with one-line summaries per file.

---

## Output Structure

```
docs/                         (or user-specified path)
  specification.md                 # overview, stack, architecture, index
  schemas.md                       # entities, fields, relations, constraints
  api.md                           # endpoint table, request/response contracts
  backend.md                       # modules, services, jobs, integrations
  frontend.md                      # pages, components, state management
  design.md                        # UI tokens, typography, colors, breakpoints
  features/
    [flow].md                      # one per identified flow
```

If a section is **not applicable** (e.g., no backend for a static site), either omit the file entirely or write a short stub explaining why it's not applicable. **Never fabricate content for a section that doesn't apply.**

---

## Per-File Content Rules

### specification.md — Entry point, scannable in ~2 minutes

- Problem statement (1–2 paragraphs)
- Stack choices table: layer → tech → why
- Architecture diagram (mermaid)
- Data flow / lifecycle (high-level)
- Project folder structure
- Index table with relative links to all sibling files
- **Clarifications** section: log each clarification exchange under `### Session YYYY-MM-DD`

### schemas.md

- Format: refer to `references/schema.md`.
- ERD (mermaid)
- Per-entity: fields using format `name : type [multiplicity] = defaultValue {propertyString}`
- Naming alternatives per table/column (≥2 options with rationale)
- Constraints (unique, nullable, indexes, lifecycle)
- No implementation hints

### api.md

- Endpoint summary table (route, method, purpose)
- Per-endpoint: request schema, response schema, error cases
- Links to `features/[flow].md` rows that exercise each endpoint
- **No implementation block** — endpoint internals belong in docs, not spec

### backend.md

- Module list table: module → responsibility → owns-schemas
- Service responsibilities
- Background jobs / workers / cron (if any)
- External integrations
- Links back to `api.md` — do **not** duplicate endpoint definitions

### frontend.md

- Page list table: route → page → purpose
- Component hierarchy for key pages
- State management strategy (≥2 options with pros/cons before recommendation)
- Data-fetching pattern
- Links to `design.md` for visuals

### features/[flow].md — One per flow

- Feature summary
- EARS scenarios: `WHEN <trigger> THEN <result>`, `WHILE <state> THEN <result>`, `IF <condition> THEN <result>`
- Given-When-Then acceptance tests
- Back-links: APIs touched → `api.md`, pages → `frontend.md`, entities → `schemas.md`

### design.md

- Design tokens: colors, typography, spacing, radii
- Component visual states (default / hover / active / disabled)
- Responsive breakpoints
- Accessibility baseline

---

## Output Rules

- High-level without over-explaining obvious things
- Detailed enough to be directly implementable by engineers
- Do not invent features or requirements unless clearly implied
- Diagrams as mermaid or ASCII
- Use `[Added]` tag for safe assumptions added during self-review
- Use `❓ Question` for ambiguous items surfaced during self-review
- Stack section in `specification.md` and state-management section in `frontend.md` must each show ≥2 alternatives with pros/cons before the recommendation

---

## Applicability Guard

Before generating, assess which files are relevant:

- No backend logic? → omit `backend.md` and `api.md` (or stub)
- No frontend? → omit `frontend.md` and `design.md` (or stub)
- Single trivial flow? → `features/` may contain just one file or be omitted

Never fabricate a file just to fill the structure.
