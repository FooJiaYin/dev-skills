---
name: spec-review
description: |
  Iteratively review and update a multi-file engineering specification
  (schemas.md + features/NN-name.md) against a source-of-truth flow document.
  Use when the user says "review spec", "spec review", "re-run the flow",
  "update features", "questions answered, re-run", or pastes new annotations
  into the source doc and asks you to propagate them. Also use to evaluate
  completeness of data models and Given-When-Then behavior scenarios.
---

# Spec Review Skill

A linear 5-phase pipeline. Phase 1 (Ingest) is conditional; phases 2–4 always apply; phase 5 (Rubric audit) is deferred until user explicitly asks. **Stop after Phase 2 to let user confirm before writing** — the user iterates faster with tight per-flow loops than with one big sweep.

```
[Phase 0] Always read fresh
    ↓
[Phase 1] Ingest (conditional)
    ↓
[Phase 2] Trace audit (per flow) → ★ pause for user confirmation
    ↓
[Phase 3] Apply (surgical edits)
    ↓
[Phase 4] Report (summary table)

[Phase 5] Rubric audit — deferred; run only when user asks
```

---

## Phase 0 — Always read fresh

Before doing anything else:

1. **Re-read `schemas.md` with the Read tool** even if you think it's already in context. The user may run multiple spec-review windows in parallel; sibling windows can mutate the schema between your turns.
2. **Re-read the target feature file** before editing it. Linter or user may have touched it.
3. Treat in-memory file state as **stale by default**.

This rule applies at the start of every spec-review invocation **and again before each surgical edit in Phase 3**.

---

## Phase 1 — Ingest (conditional)

Skip if no new input. Trigger when user pastes annotations / says "annotations updated" / there's a recent diff on the source doc.

```bash
git diff <source-doc-path>
```

Categorize every annotation:
- **Decision** → answers an existing `[Question]` or fixes a previously open behavior
- **New requirement** → adds scenario, schema field, or whole new flow
- **Clarification** → tightens an ambiguous existing scenario
- **New ambiguity** → mark as new `[Question]`

If annotations conflict with each other or with prior decisions, **stop and ask** which wins.

---

## Phase 2 — Trace audit (per flow, tight loop)

For each flow touched by Phase 1 (or for the flow the user named):

### 2a. Walk scenarios → schema

For each `S*.x` scenario in the feature file:
- Mark **Schema 是否支援 ✅ / ⚠️** by cross-checking columns / enums / FKs against current `schemas.md`
- List the **讀取** / **寫入** tables; verify every name actually exists
- Note any column the scenario implies but doesn't exist yet → schema delta

### 2b. Cross-feature behavior trace

When this scenario triggers another flow (e.g. cancel registration → notify host → flow 8):
- Add bidirectional markdown links `[NN-name.md S*.x](./NN-name.md)`
- Check the linked scenario actually exists; if not, flag it

### 2c. Pain-point reconciliation

Walk the `§7 已涵蓋痛點` table:
- 痛點解掉的標 mitigation
- 排除 scope（比賽 / referee 等）explicitly noted

### 2d. Tight-loop pause ★

**Before writing any edits**, output a **delta preview** (not the actual edits):

```markdown
## Flow N delta preview

### Questions to flip → answered
- Qx 標題 → 答案
- Qy 標題 → 答案

### New scenarios proposed
- S*.n  XXX
- S*.m  YYY

### Schema deltas needed
- table.column +ABC
- enum +DEF

### New [Questions] surfaced
- Qn. XXX
- Qm. YYY
```

Then **stop**. Wait for user to:
- Confirm → proceed to Phase 3
- Answer some open Qs → re-render preview with answers absorbed
- Correct a misread annotation → re-do Phase 1 for that item

Do not silently proceed to write edits.

---

## Phase 3 — Apply (surgical edits)

Once user confirms the delta preview:

1. **Re-read `schemas.md` again** (Phase 0 rule — parallel windows may have changed it since Phase 2)
2. Patch `schemas.md` first; tag every change line with `（Flow N delta）` or `（YYYY-MM-DD 確認）`
3. Re-read the feature file before editing it
4. Edit specific sections only:
   - `§1 概述 / 業務規則` if rule changed
   - `S*.x` scenarios (replace targeted `WHEN/THEN/讀取/寫入/Schema 是否支援` lines)
   - `§6 Open Questions`:
     - Resolved Qs → replace with one-liner `> 已答（YYYY-MM-DD）：Qx XXX — 落地於 S*.x`
     - New Qs → append as `### Qn. <title>`
   - New scenarios → append as `S*.{n+1}` or `S*.{x}b` for sub-cases
5. Never full-rewrite a feature unless its core model fundamentally changed; preserve `S*.x` numbering

Use `Edit` tool with the smallest unique `old_string` block. Don't `Read`-then-`Write` whole files — it loses sibling edits.

---

## Phase 4 — Report (end-of-turn summary)

Always close with three scannable blocks:

```markdown
## 已答 Open Questions（N 個 → 移除標記）
| Flow | Q | 答案 |
|---|---|---|

## Schema 變更
- §X table: column changes
- new tables / enums

## Features 改動
- N 個檔案 surgical edit
- M 個新檔案

## 新 Open Questions（從新標註萌生）
- Flow X Qn. ...
```

Close with a single-line next-step: "繼續下一流程 / 先回答某幾個 Q / 看 schema 最新版？"

---

## Phase 5 (deferred) — Rubric audit

Don't run automatically. Invoke only when user says "rubric audit", "full review", "audit completeness", or after a batch of flows is done and user wants a sweep.

Four checks (entity / data-model side, not scenario side):

### 5.1 Coverage of state transitions
For each entity, ask: scenarios for **created / updated / deleted / undone / merged / archived / expired / transferred**? Predefined options that might need future customization? After each action, what other data updates?

### 5.2 Given-When-Then completeness
All roles covered? All data states? Error / boundary cases? Alternative flows? Duplicates / conflicting states / expired data / invalid transitions?

### 5.3 Data model format
Each entity should follow `name : type [multiplicity] = defaultValue {propertyString}`.
Check: FKs / classes referenced but undefined; missing attributes per scenario; missing relations; constraints (unique, nullable, indexes, lifecycle); multiplicities (1, 0..1, 1..*, etc.); naming consistency; lifecycle / ownership ambiguity; cardinality mismatches; temporal attributes (createdAt, updatedAt, effectiveFrom, expiresAt); enums supporting future state transitions.

### 5.4 Integrity & normalization
Does the model support correct read/write patterns? Data integrity (no orphan refs)? Clear ownership? Proper normalization (avoid inconsistencies)? Proper denormalization (faster reads where needed)? Does each table really need to exist (can it merge)?

For optimization proposals, list 2+ alternatives with pros/cons and let user decide.

#### 5.4a Merge/split decision framework (6 axes)

When judging whether a candidate sub-entity should live as a separate table or be inlined into its parent entity, score across these axes. The more axes push toward **separate**, the stronger the case.

| Axis | Pushes toward MERGE | Pushes toward SPLIT |
|---|---|---|
| 1. Cardinality | 1:1 (every parent has one) | 1:0..1 sparse / 1:N |
| 2. Read hot path | Read on almost every parent fetch | Read only in specific flows |
| 3. Write frequency / lock contention | Same lifecycle as parent | High-frequency trigger / batch / system update |
| 4. RLS / sensitivity | Same policy as parent | Different policy (sensitive PII, financial, admin-only) |
| 5. Ownership | Parent owns and edits | Sub-system / trigger owns |
| 6. Schema evolution speed | Stable definition | Rules change frequently (e.g. derived-score algorithms) |

#### 5.4b Meta-rule (fastest filter)

> **"Will this column ever change when the parent entity isn't doing anything?"**
> YES → cache / system-maintained → keep separate (avoid row-lock contention). NO → owned by parent → safe to merge.

#### 5.4c Common candidate patterns

| Pattern | Default action | Rationale |
|---|---|---|
| **1:1 snapshot / cache table** | Merge into parent | Unless axis 3 or 6 pushes back, separate table just adds joins |
| **1:N polymorphic doc / event / log table** (discriminated by `kind` enum) | Keep separate | The discriminator is the whole point; can't flatten 1:N |
| **1:0..1 sparse role-specific profile or preferences blob** | Keep separate | Null bloat in parent + RLS policy diverges + lazy-create semantics |
| **High-frequency write cache maintained by triggers** | Keep separate | Trigger updates would contend with parent's read-heavy row lock |
| **Future-phase / reserved field for unshipped functionality** | **Delete** | Don't design for hypothetical futures; `ALTER TABLE ADD COLUMN` when the feature actually lands |
| **DEPRECATED placeholder column** | **Delete** | Deprecation isn't a state, it's a code smell — finish the migration |
| **Single-row lookup table (MVP scope only)** | Consider inline as `jsonb` or `enum` | FK + JOIN cost outweighs lookup-table flexibility at this scale |
| **Polymorphic FK with `ref_kind + ref_id`** | Keep (intentional pattern) | Don't try to replace with concrete FKs — kills the polymorphism it was designed for |
| **Sensitive columns mixed with public columns in one table** | Consider splitting sensitive subset out | Column-level RLS is doable but verbose; separate table is cleaner |
| **Append-only history / audit table** | Always separate | Never merge into snapshot/parent — append-only is its defining feature |

#### 5.4d Process

1. Score 6 axes + meta-rule sanity check.
2. Present 2+ alternatives (`merge` / `keep` / `partial`) with pros/cons → **pause for user**.
3. After confirmation: surgical edits, then `grep -rn <old_name>` across the whole spec dir to catch stale refs. Spawn parallel agents for cross-file propagation when the rename is mechanical.

Output: Phase 3 edits + Phase 4 report.

---

## Conventions that apply across all phases

### No-assumption rule
Never silently assume. Three choices:
1. **Ask the user** — small question, seconds to answer
2. **Mark `[Question]`** — when user said "leave open" or it's already unresolved
3. **Apply with `[Added]` tag** — only if mechanical / demonstrably safe (e.g. add `created_at` to a new table)

When in doubt, prefer `[Question]` over silent assumption.

### Question lifecycle
Each `[Question]` has three states:
- **Open** — listed under `### Qn. <title>` with options A/B/C and `**暫定 X**`
- **Answered** — replaced by one-liner `> 已答（YYYY-MM-DD）：Qn 標題 — 落地於 S*.x`
- **Superseded** — annotate `> 已被 Qm 取代` with link

On every Phase 1 ingest, scan `§6` of every touched feature for Qs the new annotations resolve.

### Schema delta convention
Every schema change carries provenance inline:
- `（Flow N delta）` or `（Flow N S*.x）`
- `（YYYY-MM-DD 確認）` for client-confirmed decisions
- `[Question]` if added but semantics still uncertain

### Cross-link convention
- Feature → Schema: `[schemas.md §N](../schemas.md)`
- Feature → Feature: `[NN-name.md S*.x](./NN-name.md)`
- Schema → Feature: only in 備註 column when a column's behavior depends on a specific scenario

### File scope
- `docs/spec/schemas.md` — single source of truth for entities
- `docs/spec/features/NN-name.md` — one file per flow
- Numbering: 01–10 = original flows; 11+ = derived flows from annotations
- Don't create `specification.md` / `api.md` / `backend.md` until user explicitly asks

### Linter-modified files & parallel windows
Re-read before editing. Treat any system-reminder showing modifications as **authoritative** — adapt to it; don't revert without explicit user instruction. Same applies for sibling windows mutating schema.

### When user says "繼續" / "next flow"
Take NN+1 from the source doc; run Phase 1 → Phase 2 → pause for confirmation. Don't batch multiple flows unless user says "後續每個流程" or "all remaining".

### When in doubt about scope
Ask once: "繼續寫下一流程 / 先回答某幾個 Q / 看哪個檔案的最新版？" — do not assume.
