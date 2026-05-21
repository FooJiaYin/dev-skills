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
- **Org / project scope** (only matters in this repo or org) → append to the project's `AGENTS.md`, or update the project documentation.
- **Local / personal preference** (just my workflow) → save as a memory entry, or goes to `~/.claude/CLAUDE.md` to apply across all projects.
- **Skip** — drop this finding.

For third-party/built-in skills you don't own, the "local" option becomes a wrapper or local workaround instead.

## Apply

- Ambiguous → one disambiguating follow-up `AskUserQuestion`. 
- Edits stay short — only the necessary prompt. 
- Never auto-edit before asking. Never invent findings.

## Wrap up
- After applying edits, if any edit touched a `SKILL.md` or skill supporting file, proactively suggest running `/wrap-up` to commit + report. Don't auto-fire.
