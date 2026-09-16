---
name: improve
description: Surface agent-refinement suggestions based on friction observed during the session — skill instructions, workflow sequencing, user-instructions analysis, code-review findings, or anything else that recurred. For each finding, asks the abstract scope (Global / Org / Local) without pre-binding a target, then resolves and applies the edit. AUTO-INVOKE as the final step of /wrap-up. Also use when the user says "/improve", "any refinements?", "self-improve", or "what could the agent do better?".
---

# improve

Look back at this session and surface refinements that would make next time smoother.

Examples of friction worth surfacing:
- A skill's instructions caused tool or MCP failures, missing preconditions discovered by failing, ambiguous instructions that needed user clarification, user correction or mid-skill corrections. 
- Sequencing or handoffs between skills caused redundant work or wrong order.
- Analyze user instructions, corrections, and preferences, and also analyze if the agent's behavior aligns with what the user actually wants in the first place.
- Code-review findings (read `REVIEW.md` if present, plus any code-review output earlier in the session) — find issues that should become agent-writing-code rules.

## Surface

Surface a "Refinement suggestion:" each finding must point out a failing step and propose a concrete edit. Suggest and ask; do not auto-edit. 

## Ask scope

`AskUserQuestion` (header: `Scope`) with suggested scope:
- **Skill** (applies anywhere the skill runs) → edit the skill file itself (typically under `~/agent-skills/` or `~/.claude/skills/`).
- **Org / project scope** (only matters in this repo or org) → write it where it will actually be read. A topically-relevant doc (e.g. `docs/frontend.md`, `docs/services/auth.md`) is often the most natural home, but a rule in a doc agents don't routinely load is effectively dead. So: for an agent-writing-code rule that must be enforced, prefer the **auto-loaded** `AGENTS.md` / `CLAUDE.md`; or place it in the topical doc **and** add a one-line pointer from `AGENTS.md`. Drop it solely into a topical doc only when a skill/workflow reliably reads that doc for the relevant task.
- **Code comment (function-local)** → when a finding only matters for one specific function / call-site (a gotcha or debug hint scoped to that code, not a general rule), add a short reminder comment right at that function instead of a doc — the next reader sees it exactly where it applies.
- **Local / personal preference** (just my workflow) → save as a memory entry, or goes to `~/.claude/CLAUDE.md` to apply across all projects.
- **Skip** — drop this finding.

For third-party/built-in skills you don't own, the "local" option becomes a wrapper or local workaround instead.

## Apply

- Ambiguous → one disambiguating follow-up `AskUserQuestion`. 
- Edits stay short — only the necessary prompt. 
- Never auto-edit before asking. Never invent findings.

## Wrap up

If any edit touched a `SKILL.md` or skill supporting file, **commit it here — don't hand it to `/wrap-up`.** (Full commits at step 7, before improve runs; Quick runs in the project repo, not the skill repo. Either way the skill edit is left dirty.)

1. Group the edited skill files by `git -C <dir> rev-parse --show-toplevel`. Run 2–4 per repo.
2. `git diff <file>` each one — skill repos routinely carry other sessions' leftovers, so confirm every hunk is yours and commit with an explicit pathspec.
3. Write a short report via `/report` to **`<skill repo>/docs/reports/YYYY-MM-DD-<title>.md`** — inside the repo, so it ships in the same commit. Not the parent folder.
4. `AskUserQuestion` to confirm scope + message, then `git -C <repo> commit -m "improve(<skills>)：<摘要>" -- <files> <report>` + push per `wrap-up/commit.md`.
5. Repo has org fork remotes → print one line: `N 筆 improve 未同步到 org forks，之後跑 /sync-org-forks`. Don't run it.

Skip `/update-docs`, `rename-session` and deploy detection — a skill edit needs none of them, and `rename-session` would rename the *project* session.
