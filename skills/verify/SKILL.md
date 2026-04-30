---
name: verify
description: Execute the implementation plan's Test plan / Verification section. Reads the relevant plan file, runs each listed check (type-check, lint, unit/integration tests, manual UI walks), skips checks already run earlier in the session if no relevant code has changed since, and reports pass/fail per item. Does NOT author new tests. Use when the user says "verify", "run the test plan", "check it works", or invokes /verify. Also invoked by /wrap-up step 1.
---

# verify — execute the implementation plan's test plan

This skill runs the verification checks defined in the implementation plan. It is a runner, not an author — it does not invent new tests.

## 1. Locate the plan

- Look for the implementation plan file the user has been working from. Common locations:
  - `~/.claude/plans/*.md` (most recently modified is usually correct)
  - A planning doc the user explicitly pointed to in this conversation
  - A `docs/plans/` or similar folder in the project
- If multiple candidates exist and it's ambiguous, ask the user which plan to verify against. Don't guess.
- If no plan exists, or the plan has no **Test plan** / **Verification** section, **stop and ask the user** — don't invent checks.

## 2. Read the Test plan section

Parse each numbered check. For each item, identify:

- What the check is (type-check, lint, unit test, integration test, manual UI walk, smoke test, etc.)
- The command or action (if specified) or the project-type-derived command (if implied)
- The scope of files it covers (so step 3 can decide skip vs run)

## 3. Decide skip vs run

For each check, decide:

- **Skip** if the same check was already run earlier in this session AND no relevant code has changed since (no edits to files in scope of that check after the earlier run).
- **Run** otherwise.

When skipping, state which check was skipped and reference the earlier passing result so the user can see coverage isn't being silently dropped.

## 4. Resolve commands

Detect project type only to resolve commands the plan refers to by name:

- `package.json` present → use `yarn` (or `pnpm` if `pnpm-lock.yaml` is present). Per global rule, prefer `yarn` over `npm`.
- `pyproject.toml` / `requirements.txt` present → activate `.venv`/`env` first if it exists (`source .venv/bin/activate`), then `pytest`, `ruff`, `mypy`, etc.
- `Cargo.toml` → `cargo test`, `cargo clippy`, `cargo fmt --check`.
- `go.mod` → `go test ./...`, `go vet`, `golangci-lint`.

If the plan specifies an exact command, use it verbatim; do not substitute.

## 5. Execute and report

- Run each non-skipped check.
- For UI / manual checks, follow the plan's instructions (e.g., "start dev server, walk golden path"); state explicitly when manual verification was skipped because no UI is reachable.
- Report per item: **pass** / **fail** / **skipped — already passed at \<point\>** / **deferred — \<reason\>** (e.g., "requires fresh session", "requires real test project").
- If anything fails, **stop here** — surface the failure with the failing output. Do not continue running later checks; do not paper over.

## Guardrails

- Never author new tests. If the plan's Test plan is incomplete or missing items, surface the gap to the user — don't fill it in silently.
- Never edit code to make a failing test pass. Just run and report.
- If no plan or no Test plan section exists, stop and ask.
- Tests are non-negotiable — flag clearly when something can't be run, don't silently skip.
