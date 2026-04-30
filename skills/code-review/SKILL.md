---
name: code-review
description: Multi-agent review of the local git diff. Spawns parallel agents covering bugs+security, CLAUDE.md adherence, git history, plan adherence, and quality+architecture; filters findings through a confidence rubric (≥80); writes REVIEW.md. Use when the user says "review my changes", "review this branch", "code review", or invokes /code-review.
---

# Code Review

You are the orchestrator of a multi-agent code review. You do not analyze code yourself — you fan out to specialized subagents, collect their findings, score them for confidence, and write a single `REVIEW.md` artifact.

## Inputs

The user may pass a base ref (e.g. `main`, `HEAD~3`) or a plan file path. If neither, infer them in Phase 0 / Phase 1.

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

### Phase 1 — Context Gathering (one Haiku agent, sequential)

Spawn a single Haiku agent with this task:

> Given the file list `<FILES>` and repo root, return:
> 1. The path to the root `CLAUDE.md` if it exists, plus any `CLAUDE.md` in the directories of changed files. **Paths only, do not read contents.**
> 2. The path to a plan/spec file if one exists. Look in: a path the user passed (`<PLAN_HINT>`), `.planning/`, `docs/plans/`, `docs/specs/`, root `PLAN.md`. Return the first match or `null`.
> 3. A 1–2 sentence summary of the diff's apparent intent, based on `git diff --stat $BASE..HEAD` and the file paths. Do not read file contents.

Store the result as `CONTEXT = {claude_md_paths, plan_path, intent_summary}`.

### Phase 2 — Parallel Fan-Out (5 Sonnet agents in ONE tool-call block)

Spawn all five in a single message. Each receives `BASE`, `HEAD`, the file list, and `CONTEXT`. Each returns `[{description, evidence, source_aspect}]` where `source_aspect` is one of `bugs-security`, `claude-md`, `git-history`, `plan-adherence`, `quality-architecture`.

Agent prompts live in:
- `agents/bugs-security.md`
- `agents/claude-md.md`
- `agents/git-history.md`
- `agents/plan-adherence.md`
- `agents/quality-architecture.md`

Read the prompt file, substitute `{BASE}`, `{HEAD}`, `{FILES}`, `{CLAUDE_MD_PATHS}`, `{PLAN_PATH}`, `{INTENT}`, and pass the result to the subagent.

**Agent modes:** Agents A (`bugs-security`) and E (`quality-architecture`) operate in **adversarial-recall mode** — surface every plausible candidate; the downstream confidence filter prunes false positives. Agents B (`claude-md`), C (`git-history`), and D (`plan-adherence`) operate in **citation-only mode** — every finding must quote a verbatim source (CLAUDE.md rule, commit/PR reference, or plan section). Both modes feed the same Phase 3 scorer.

### Phase 3 — Confidence Scoring (parallel Haiku agents, one per finding)

For each finding from Phase 2, spawn a Haiku scorer in parallel (single tool-call block). The scorer receives:
- The finding (`description`, `evidence`, `source_aspect`)
- The diff (`git diff $BASE..HEAD` for the affected file)
- The CLAUDE.md path list

The scorer returns a single integer 0–100 per the **Confidence Rubric** below. For `claude-md` findings, the scorer must open the cited CLAUDE.md and verify it *literally* contains the rule the finding cites — if not, score 0.

### Phase 4 — Filter & Format

1. Drop every finding with confidence < 80.
2. If zero remain → write `REVIEW.md` with `status: clean` (template below) and stop.
3. Else → map confidence to severity:
   - 95–100 → Critical
   - 80–94 → Warning
4. Write `REVIEW.md` per the **Output Format** template, grouped first by `source_aspect`, then by severity within each group.

### Phase 5 — Summary to User

One line: `Found N high-confidence issues. See REVIEW.md.` (or `Clean — no issues found above the confidence threshold.` / `Skipped — no source files in diff scope.`).

Do not post anywhere external. No `gh pr comment`. Local-only.

---

## Confidence Rubric

For each issue, score 0–100:

- **0** — Not confident at all. False positive that doesn't stand up to light scrutiny, or a pre-existing issue.
- **25** — Somewhat confident. Might be a real issue, might be a false positive. The scorer wasn't able to verify. Stylistic issues not explicitly called out in CLAUDE.md belong here.
- **50** — Moderately confident. Verified as a real issue, but might be a nitpick or rare in practice. Not very important relative to the rest of the diff.
- **75** — Highly confident. Double-checked. Very likely real, will be hit in practice. The PR's existing approach is insufficient. Important and directly impacts functionality, or directly mentioned in the relevant CLAUDE.md.
- **100** — Absolutely certain. Double-checked and confirmed. Will happen frequently in practice. Evidence directly confirms it.

---

## False-Positive Categories

Treat these as automatic 0 scores:

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

When writing finding text:
- **Never** use "check", "confirm", "verify", or "ensure". Be declarative.
- Don't explain what the code does back to the author — they wrote it.
- One issue per finding entry. If duplicated across files, state it once and list the other locations as a single line.
- Reference only changed lines (those beginning with `+` or `-` in the diff), not surrounding context lines.

---

## Output Format

Write to `REVIEW.md` in the repo root.

### Frontmatter (YAML)

```yaml
---
reviewed: <ISO-8601 timestamp>
base: <BASE ref>
head: <HEAD sha>
files_reviewed_list:
  - path/to/file1.ext
  - path/to/file2.ext
findings:
  critical: N
  warning: N
  total: N
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

**Status:** clean — N files reviewed, no findings above the confidence threshold (80).

**Files reviewed:** N
**Diff range:** `<BASE>..<HEAD>`
**Intent:** <intent_summary from Phase 1>
```

### Body — `status: issues_found`

```markdown
# Code Review

**Status:** issues_found — N findings (X critical, Y warning).

**Files reviewed:** N
**Diff range:** `<BASE>..<HEAD>`
**Intent:** <intent_summary from Phase 1>

## Bugs & Security

### CR-01 — <short title>

**File:** `path/to/file.ext:42`
**Severity:** Critical
**Confidence:** 95
**Issue:** <declarative description, no "check/verify/ensure">
**Fix:**
```language
<concrete code snippet or one-line suggestion>
```

### WR-01 — <short title>

**File:** `path/to/file.ext:88`
**Severity:** Warning
**Confidence:** 82
**Issue:** <description>
**Fix:** <suggestion>

## CLAUDE.md Adherence

### WR-02 — <short title>

**File:** `path/to/file.ext:12`
**Severity:** Warning
**Confidence:** 88
**CLAUDE.md rule:** "<verbatim quote>" (`<path/to/CLAUDE.md>`)
**Issue:** <description>
**Fix:** <suggestion>

## Git History

### WR-03 — <short title>

**File:** `path/to/file.ext:55`
**Severity:** Warning
**Confidence:** 85
**Historical context:** <commit sha or PR # and what it tells us>
**Issue:** <description>
**Fix:** <suggestion>

## Quality & Architecture

### WR-04 — <short title>

**File:** `path/to/file.ext:33`
**Severity:** Warning
**Confidence:** 84
**Anchor:** <path/to/neighbor.ext:line — what pattern it establishes, OR path/to/duplicate.ext:line — what's duplicated>
**Issue:** <description>
**Fix:** <suggestion>

## Plan Adherence

### CR-02 — <short title>

**Plan section:** <heading or quote from plan file> (`<plan path>`)
**Severity:** Critical
**Confidence:** 96
**Issue:** <description of missing requirement / scope creep / undocumented breaking change>
**Fix:** <suggestion>
```

Omit any section whose finding count is zero. ID prefix is `CR-` for Critical, `WR-` for Warning, numbered globally.

---

## Critical Rules

- **Read-only.** Do not modify source files. The only file you may write is `REVIEW.md`.
- **Don't run typecheck / lint / tests.** CI handles those.
- **Cite `file:line` for every finding.** Never "somewhere in this file".
- **Skip findings on lines the diff doesn't touch.**
- **Phase 2 must be parallel.** Spawn all five fan-out agents in a single tool-call block, not sequentially.
- **Phase 3 must be parallel.** Spawn all scorers in one tool-call block.
- **Don't paraphrase the rubric or false-positive list when passing to scorer agents** — copy them verbatim.
