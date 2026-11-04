---
name: code-review
description: Deep multi-agent review run on demand BEFORE MERGING A BRANCH or after a large refactor — not on every wrap-up. Diffs merge-base(main)..HEAD by default, picks reviewer agents by what the diff touches (bugs+security, standards, performance, quality+architecture; git history on request), runs a yes/no verifier per finding, and writes REVIEW.md. Also has a whole-tree mode (`/code-review tree [glob]`, or wording like 「審核架構／有沒有重複」) that audits the current source for duplication and missing abstractions instead of a diff. Use when the user says "review this branch", "deep review", "code review", "審核架構", or invokes /code-review. For the routine end-of-session check use quick-review. Supersedes the built-in /code-review in repos using dev-skills — invoke only this one.
---

# Code Review

You are the orchestrator of a multi-agent code review. When delegation is available, fan out to the specialized subagents the diff calls for, collect their findings, verify each one, and write a single `REVIEW.md` artifact. Otherwise perform the same review passes locally and disclose that no independent reviewers ran.

## Instruction-source compatibility

The `standards` agent (formerly `claude-md`), the legacy `claude_md_paths` field, and `{CLAUDE_MD_PATHS}` placeholder represent applicable project instructions from **both `AGENTS.md` and `CLAUDE.md`**. Pass this binding explicitly to every reviewer and verifier. References below to CLAUDE.md rules include those AGENTS.md rules; cite the actual source file verbatim. Label the report section "Standards".

## Inputs

The user may pass a base ref (e.g. `main`, `HEAD~3`) and `--agents a,b` to force a reviewer set. If no base, infer it in Phase 0. Requirement / plan coverage is not checked here — that belongs to `/align`.

**Tree mode.** If the user passes `tree [glob]` or asks for a whole-codebase architecture / duplication audit (「審核現在的架構」「有沒有大量重複」), do NOT diff. Scope = the glob (default `src/**` minus generated files), working tree as-is. Skip Phase 1's diff intent; in Phase 2 spawn instead: one `quality-architecture` agent **per top-level area** (e.g. `app/(main)/products`, `app/(main)/admin`, `app/(main)/suppliers` + shared) plus **one cross-cutting duplication agent** over the whole scope (hunts pattern families with grep: action-runner boilerplate, page shells, table/select/label scaffolds, enum lists, repeated Tailwind strings), plus `standards`; `bugs-security` / `performance` optional, `git-history` skipped. Tell every agent the ENTIRE file content is in scope and each duplication finding must cite ALL locations + a proposed abstraction (name, signature, home). In Phase 3 pass the verifier blocklist verbatim **plus an override note**: false-positive categories 1 and 8 do not apply in tree mode; concrete, location-cited duplication is the requested deliverable, not a "general code-quality complaint". Frontmatter `base`/`head` = current HEAD + "working tree"; add a `scope:` line.

Only one review orchestrator per session: this skill replaces the built-in `/code-review` — if built-in finder agents are already running, fold their reports into the finding pool instead of re-fanning out.

## Orchestrator Flow

### Phase 0 — Eligibility & Scope

1. Confirm git repo: `git rev-parse --git-dir`. If this fails, stop and tell the user the skill needs a git repository.
2. Determine `BASE`:
   - If user passed a base ref, use it.
   - Else: `git merge-base HEAD origin/main` (try `origin/master`, then local `main`/`master`).
   - Else: fall back to `HEAD~1` and warn the user that the diff base is approximate.
3. Compute changed files:
   ```bash
   git diff --name-only $BASE..HEAD -- . \
     ':!.planning/' ':!ROADMAP.md' ':!STATE.md' \
     ':!*-SUMMARY.md' ':!*-VERIFICATION.md' ':!*-PLAN.md' \
     ':!package-lock.json' ':!yarn.lock' ':!pnpm-lock.yaml' \
     ':!Gemfile.lock' ':!poetry.lock' ':!*.min.js' ':!*.bundle.js' \
     ':!dist/' ':!build/'
   ```
4. If the resulting list is empty: write `REVIEW.md` with `status: skipped` (template below) and stop.

### Phase 1 — Context Gathering (one agent, sequential)

Spawn a single context agent (Claude: Haiku; Codex: inherited model) with this task:

> Given the file list `<FILES>` and repo root, return:
> 1. The paths to applicable `AGENTS.md` and compatibility `CLAUDE.md` files from the root through the changed-file directories. Deduplicate symlinks; prefer `AGENTS.md` in the same directory. **Paths only, do not read contents.**
> 2. `has_design_md`: whether `DESIGN.md` exists at the repo root.
> 3. `diff_type`: one or more of `logic` / `style-only` / `docs-only` / `query-touching` (DB queries, loops over data, list renders, API handlers), from `git diff --stat $BASE..HEAD`, the file paths and a skim of the hunks.
> 4. A 1–2 sentence summary of the diff's apparent intent. Also report whether the diff adds new files / abstraction layers and its total changed-line count.

Store the result as `CONTEXT = {claude_md_paths, has_design_md, diff_type, intent_summary, adds_files, changed_lines}`.

### Phase 2 — Routed Fan-Out

Pick reviewers from `CONTEXT` (or exactly the `--agents a,b` set, if passed):

| agent | runs when |
|---|---|
| `bugs-security` | diff has logic changes (not only copy / styles / docs) |
| `standards` | always — two rounds, below |
| `performance` | `query-touching` |
| `quality-architecture` | new files / abstraction layers, or `changed_lines` > 300 |
| `git-history` | only when the user asks |

Record which agents ran and which were skipped, with the reason; this goes at the top of `REVIEW.md`.

Claude: prefer Sonnet reviewers. Codex: inherit the parent model. Spawn the chosen reviewers in parallel up to the host's concurrency limit. Read each prompt from `agents/<name>.md`, substitute `{BASE}`, `{HEAD}`, `{FILES}`, `{CLAUDE_MD_PATHS}`, `{HAS_DESIGN_MD}`, `{INTENT}`, and pass the result. Each returns `[{description, severity, evidence, source_aspect}]`; the reviewer assigns severity (Critical / Warning / Suggestion / Nit).

**Standards rounds.** Round 1: the agent reviews freely against the project instructions. Round 2: once it returns, SendMessage it the contents of `../../shared/review/commons.md` (relative to this skill's directory; plus `docs/review-standard.md` if the repo has one) and ask for findings not already reported. On hosts without SendMessage, spawn a second standards agent given the commons and the round-1 findings. The order keeps the checklist from anchoring the first pass.

**Agent modes:** `bugs-security`, `quality-architecture` and `performance` run in **adversarial-recall mode** — surface every plausible candidate; the verifier prunes. `standards` and `git-history` run in **citation-only mode** — every finding quotes a verbatim source (instruction / commons rule, commit or PR reference).

### Phase 3 — Verification (one binary verifier per finding)

**Standards findings skip the verifier:** the orchestrator greps the cited file for the quoted rule; keep the finding if the quote is there, drop it if not.

For every other finding, spawn a verifier (Claude: Haiku; Codex: inherited model) in bounded parallel batches. Check its status before retrying a failed verifier; do not restart user-interrupted work without authorization. If delegation is unavailable, verify locally and disclose the loss of independent verification. The verifier receives the finding, the diff for the affected file (`git diff $BASE..HEAD -- <file>`), the instruction path list, and the **False-Positive Categories** below verbatim. It returns `real` or `not real` plus a one-line reason. It does not change severity. Fixed checks:

- Any False-Positive Category → `not real`.
- `performance`: `evidence.cost_model` must have all four fields (`hot_path_class`, `frequency`, `per_call`, `verdict`) with concrete values; vague or missing values, `init/cold` with no startup-budget evidence, or `verdict: negligible` → `not real`.
- A **DB schema fact** (a column / table / enum / RPC exists or not) must be confirmed against an **authoritative live source** — generated types (e.g. `database.types.ts`), the live DB via Supabase MCP, or migrations confirmed applied to remote — **NOT** local `docs/migrations/` or `docs/schemas/` files, which drift. Unconfirmable → `not real`.

### Phase 4 — Filter & Format

1. Drop findings verified `not real` (and standards findings whose quote wasn't found).
2. If zero remain → write `REVIEW.md` with `status: clean` (template below) and stop.
3. Else → write `REVIEW.md` per the **Output Format** template, grouped by `source_aspect`, sorted Critical → Warning → Suggestion → Nit within each group.

### Phase 5 — Summary to User

One line: `Found N findings (X critical, Y warning, Z suggestion, W nit). See REVIEW.md.` (or `Clean — no findings survived verification.` / `Skipped — no source files in diff scope.`).

Do not post anywhere external. No `gh pr comment`. Local-only.

---

## False-Positive Categories

The verifier's fixed blocklist — any match is `not real`:

1. **Pre-existing issues** — present before this diff.
2. **Bug-shaped non-bugs** — looks like a bug but isn't.
3. **Pedantic nitpicks** — a senior engineer wouldn't call this out.
4. **Linter / typechecker / compiler-catchable** — missing imports, type errors, broken tests, formatting, pedantic style. CI handles these.
5. **General code-quality complaints** — lack of test coverage, generic security concerns, poor documentation — *unless* CLAUDE.md explicitly requires it.
6. **Issues silenced by the author** — e.g., a lint-ignore comment on the line.
7. **Intentional behavior changes** related to the broader change.
8. **Real issues on unmodified lines** — only flag issues on lines the diff actually touches.

---

## Tone Constraints

Finding text follows the comment rules in [`../../shared/review/commons.md`](../../shared/review/commons.md) §1.

---

## Output Format

Write to `REVIEW.md` in the repo root — the user's project checkout, never a temporary worktree or scratch copy (those get wiped). Add `REVIEW.md` to `.gitignore` if it isn't ignored yet.

### Frontmatter (YAML)

```yaml
---
reviewed: <ISO-8601 timestamp>
base: <BASE ref>
head: <HEAD sha>
session: <current session ID>   # lets /quick-review avoid overwriting this file
files_reviewed_list:
  - path/to/file1.ext
  - path/to/file2.ext
findings:
  critical: N
  warning: N
  suggestion: N
  nit: N
  total: N
agents_ran: [standards, bugs-security, ...]
agents_skipped: {performance: "no query-touching changes", ...}
status: clean | issues_found | skipped
---
```

### Body — `status: skipped`

```markdown
# Code Review

**Status:** skipped — no source files in diff scope after filtering planning artifacts, lock files, and generated files.
```

### Body — `status: clean`

```markdown
# Code Review

**Status:** clean — N files reviewed, no findings survived verification.

**Agents:** ran <list>; skipped <agent> (<reason>), ...
**Files reviewed:** N
**Diff range:** `<BASE>..<HEAD>`
**Intent:** <intent_summary from Phase 1>
```

### Body — `status: issues_found`

````markdown
# Code Review

**Status:** issues_found — N findings (X critical, Y warning, Z suggestion, W nit).

**Agents:** ran <list>; skipped <agent> (<reason>), ...
**Files reviewed:** N
**Diff range:** `<BASE>..<HEAD>`
**Intent:** <intent_summary from Phase 1>

## Bugs & Security

### CR-01 — <short title>

**File:** `path/to/file.ext:42`
**Severity:** Critical
**Issue:** <declarative description, no "check/verify/ensure">
**Fix:**
```language
<concrete code snippet or one-line suggestion>
```

### WR-01 — <short title>

**File:** `path/to/file.ext:88`
**Severity:** Warning
**Issue:** <description>
**Fix:** <suggestion>

## Standards

### WR-02 — <short title>

**File:** `path/to/file.ext:12`
**Severity:** Warning
**Rule:** "<verbatim quote>" (`<path/to/AGENTS.md | CLAUDE.md | shared/review/commons.md>`)
**Issue:** <description>
**Fix:** <suggestion>

## Git History

### WR-03 — <short title>

**File:** `path/to/file.ext:55`
**Severity:** Warning
**Historical context:** <commit sha or PR # and what it tells us>
**Issue:** <description>
**Fix:** <suggestion>

## Quality & Architecture

### WR-04 — <short title>

**File:** `path/to/file.ext:33`
**Severity:** Warning
**Anchor:** <path/to/neighbor.ext:line — what pattern it establishes, OR path/to/duplicate.ext:line — what's duplicated>
**Issue:** <description>
**Fix:** <suggestion>

### SR-01 — <short title>

**File:** `path/to/file.ext:71`
**Severity:** Suggestion
**Anchor:** <path/to/neighbor.ext:line — what pattern it establishes, OR path/to/duplicate.ext:line — what's duplicated>
**Issue:** <description>
**Fix:** <suggestion>

## Performance

### WR-05 — <short title>

**File:** `path/to/file.ext:47-49`
**Severity:** Warning
**Hot path:** <hot_path_class — request-path | loop-body | render-path | batch/cron>
**Frequency:** <e.g., per HTTP request × len(userIds), unbounded>
**Per-call cost:** <e.g., DB roundtrip>
**Verdict:** <moderate | high | critical>
**Issue:** <description>
**Fix:** <suggestion>

### NR-01 — <short title>

**File:** `path/to/file.ext:104`
**Severity:** Nit
**Hot path:** <hot_path_class>
**Frequency:** <e.g., once per request>
**Per-call cost:** <e.g., extra allocation>
**Verdict:** <moderate>
**Issue:** <description>
**Fix:** <suggestion>
````

Omit any section whose finding count is zero. ID prefixes: `CR-` for Critical, `WR-` for Warning, `SR-` for Suggestion, `NR-` for Nit. Each prefix is its own counter.

---

## Applying Fixes

If the user asks to fix the findings after `REVIEW.md` is written: group findings by file, spawn one subagent per file in a single parallel tool-call block, each receiving all findings for its file. Serialize cross-file findings (e.g. signature changes that ripple to callers) into one agent.

---

## Critical Rules

- **Read-only.** Do not modify source files. The only file you may write is `REVIEW.md`.
- **Don't run typecheck / lint / tests.** CI handles those.
- **Cite `file:line` for every finding.** Never "somewhere in this file".
- **Skip findings on lines the diff doesn't touch.**
- **Phase 2:** use parallel agents within the host's available slots; use the disclosed local fallback if delegation is unavailable.
- **Phase 3:** batch independent verifiers within the host's available slots.
- **Don't paraphrase the false-positive list when passing it to verifiers** — copy it verbatim.
