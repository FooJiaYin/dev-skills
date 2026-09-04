---
name: report
description: Analyze the current chat conversation, file changes, and actions taken to create a comprehensive report. Saves to docs/reports/YYYY-MM-DD-[title].md. Also exports the raw conversation transcript to markdown via `/report transcript`.
argument-hint: "[optional title] | transcript [--full]"
---

Analyze the current chat conversation, file changes, and actions taken to create a comprehensive report using the specified template.

Save the report as `docs/reports/YYYY-MM-DD-[title].md`

The date should be the date when the task is mainly worked on, not the date when the report is generated.

## Transcript Export (`/report transcript`)

When the user asks for the **raw conversation** rather than a synthesized report
("export this chat", "dump the transcript", `/report transcript`), skip every
other step in this skill and run:

```bash
python3 <skill-base>/export-transcript.py [--full] [-o PATH] [--session UUID] [--since ISO]
```

- Default output: `docs/reports/YYYY-MM-DD-<title>-transcript.md`, relative to the cwd.
- Default body: user prompts + assistant prose only (IDE wrappers, system-reminders
  and tool traffic stripped; `AskUserQuestion` answers kept).
- `--full` adds thinking blocks, tool calls, and truncated tool results.
- Session resolution: `--session` > `$CLAUDE_CODE_SESSION_ID` > newest transcript
  for the cwd. `--session` takes a uuid or a path (a `subagents/*.jsonl` path
  exports that subagent).

Do not read the jsonl or hand-assemble the transcript yourself — the script does it.
This is an export, not a report: no template, no plan integration, no session rename.

## Pre-flight: split decision

Before resolving the target file or choosing a template, decide whether to write multiple reports:

**Skill edits split into their own report.** If the session touched any `SKILL.md`, its siblings, or files under a `.claude/skills/` or `*-skills/` directory, ask whether to split (default yes). The skill report saves to the nearest ancestor of the skill file that contains a `docs/reports/` directory, as `<that-root>/docs/reports/YYYY-MM-DD-<title>.md`.

**Unrelated topics split.** If the conversation covers multiple **unrelated** tasks (e.g. designing a framework AND building a CLI tool), ask the user whether to split into separate reports. Each report should be a self-contained document with its own title and file.

**Distinct deliverable = its own report.** A distinct deliverable or implementation phase gets its OWN report file **even when related to a prior report** — never hand-append a feature write-up into another report's body. Create a new file, cross-reference the related report, and still run the Plan Integration (`attach-plan.sh`) step on the new file. If you hand-authored a report outside this skill, you still owe it the attach-plan step — don't skip it.

For multiple reports: §0 (target file) and the template choice apply per report. Plan integration and session rename happen after all reports are written.

## 0. Resolve Target File (lifecycle-aware)

Before generating, decide whether this report is **appending to an existing `docs/tasks/<slug>.md`** (Notion-task lifecycle path) or **synthesizing fresh from conversation** (today's behavior).

1. **Scan the conversation** for explicit Notion task URLs or task-name mentions (e.g. "working on auto-notification").
2. **Match against `docs/tasks/*.md`** via frontmatter `notion.page` URL or filename slug.
3. **If matched** → use that file as the target. Skip to "Target = task file" below.
4. **Otherwise**, scan `docs/tasks/*.md` for files with `notion.page` frontmatter:
   - 0 matches → fresh report (today's behavior); see "Target = fresh".
   - 1 match → use it as the target.
   - 2+ matches → prompt via `AskUserQuestion` which file to report on; offer a "fresh report (no task file)" escape hatch.

**When the session's work genuinely spans multiple fetched tasks** (e.g. you `/fetch-task`'d two tasks and implemented both — a player-side and a host-side of one feature), don't force-pick one or synthesize a single fresh report: **split per task**. Append the relevant slice of `# Changes Made` / `# Result` to *each* matched task file (cross-reference the sibling report), then run the per-target steps (rename into `docs/reports/`, plan-attach) once per file. The "pick one" prompt is for ambiguity over *which* task; it is not for collapsing multi-task work into one report.

### Target = task file

When a task file is resolved:

1. **Refresh `# Context` from Notion first.** Invoke `/fetch-task <task-url>` (URL pulled from the task file's `notion.page` frontmatter). This guarantees the report carries the latest meeting context, including any subsections appended by `/create-tasks` while the dev was working. Skip this step if the file has no `notion.page` frontmatter (orphaned local file).
2. **Append, don't synthesize.** Generate `# Changes Made` and `# Result` (plus optional `# Updates` / `# Unsolved Issues`) from conversation + file diff, and **append** them to the existing task file. `# Context` is preserved from `/fetch-task`. `# Plan` is inserted by the existing `attach-plan.sh prepend` flow — but the insertion point shifts from "after line 1" to **"after the `# Context` block"** when the file came from `/fetch-task`.
3. **Final section order:** `# Context` → `# Plan` → `# Changes Made` → `# Result` (→ `# Updates` / `# Unsolved Issues` if applicable).
4. **Dev-authored notes inside `# Context`** are treated as part of context — they may be overwritten on the next `/fetch-task`. That's the convention; documented via the managed-marker comment.
5. **Rename the file.** `docs/tasks/<slug>.md` → `docs/reports/<YYYY-MM-DD>-<slug>.md`. The frontmatter (`notion.page`, `notion.last_synced`) carries over unchanged.

### Target = fresh

No task file detected → **first scan `docs/reports/` for a very recent report on the SAME feature/topic** (same-day or adjacent-day filename date + overlapping subject). **If one is found, ASK the user** via `AskUserQuestion` whether to **append the delta to that existing report** (additive edits + dated `_(YYYY-MM-DD)_` markers) or **create a new file** — do NOT auto-decide. If none found, or the user picks new: synthesize a fresh `docs/reports/YYYY-MM-DD-<title>.md` from conversation. **No `/fetch-task` call.** Auto-refresh on reference applies only when a task file is detected.

## Report Generation Process

1. **Analyze Chat History**: Review the conversation to capture only the core issue, discussion points and decisions made, solutions attempted and their outcomes
2. **Examine File Changes**: Mention only relevant changes and the main purpose of the changes
3. **Summarize Actions Taken**: commands executed, deployments, or test runs

## Available Report Templates

Please choose a template to follow:

1. Task Report: (`./templates/report-task.md`)
2. Bug Fix Report: (`./templates/report-bug-fix.md`)
3. Planning Report: (`./templates/report-planning.md`) — for brainstorming, design discussions, trade-off analysis, decision records. May cover multiple related topics. **STRONG DEFAULT: raw conversation paste per topic.** Only upgrade a topic to the structured form (Discussion / Solutions / Decision) when the topic spanned **7 or more conversation turns** (back-and-forth exchanges on the same topic). A short topic stays as raw paste even if it contains a decision, compared options, or discussed trade-offs. Decide per topic when first drafting it — don't switch modes mid-topic. Mixed modes across topics in one report are fine.

## Issue Resolution

If `/code-review` ran (or the conversation surfaced issues another way), record what happened to each issue:

**Solved issues** → write into the `# Updates` section of the report template (already present in `templates/report-task.md` and `templates/report-bug-fix.md`). For each issue fixed during this session, add a one-line entry:

- `- Fixed [severity] file:line — what the issue was and what the fix was`

**Unsolved issues** → add a new top-level `# Unsolved Issues` section to the report (after `# Result`). For each finding that was surfaced but NOT fixed, add a one-line bullet:

- `- [severity] file:line — short description (deferred because: reason)`

Sources for both buckets:
1. `REVIEW.md` at repo root — `/code-review`'s output with confidence-scored findings.
2. The conversation — TODOs the user said "leave for later", bugs surfaced and acknowledged.
3. Failed verification steps — if `/verify` failed and the user chose to ship anyway.

If there are no issues in a bucket, omit that bucket's content — do not stub the `# Updates` section with "no fixes" or write an empty `# Unsolved Issues` heading.

## Plan Integration

After writing the report, if a plan was used during the conversation:

1. Identify the plan file path (e.g. `~/.claude/plans/some-plan-name.md`)
2. Run `bash <skill-base>/attach-plan.sh <mode> <plan> <report>` where `<skill-base>` is announced at skill load. If unknown, fallback: `find ~/agent-skills ~/.claude -name attach-plan.sh -path '*/report/*' | head -1`.
   - `<mode>` is `prepend` for Task / Bug Fix reports, `append` for Planning reports

Do NOT read the plan file yourself. The script handles everything.
If no plan was used, skip this step.

**Run this unconditionally whenever a plan was used this session** — do NOT skip on a subjective "the plan's topic doesn't match the report" judgment. The plan file may have been overwritten/rewritten mid-session (e.g. a planning task then a different implementation task reusing the same plan file), so its current content often *does* match the report even when it didn't earlier. If genuinely unrelated, still attach it and note so in the report; never silently omit.

For multiple reports: run the script once per report with the matching plan file and mode.

## Session Rename

After saving the report (and any plan integration), invoke the `rename-session` skill with the report's `YYYY-MM-DD-[title]` as the argument so the session name matches the report. For multiple reports, use the first report's title.

## Report Writing Guidelines

1. **Prioritize final file changes**: User may make edits to the file out of the conversation history. Read relevant files to understand the final code.
2. **Be short**: Each section should be 1–3 sentences max. Description should be brief.
   instead of pasting the whole code, try to use high level descriptions in bullet point form. only include lines of code that is relevant and significant.
3. **Be Specific**: Include exact error messages, file paths, and code snippets only if relevant
4. **Step-by-Step**: Show what was tried and what finally worked
5. **Include Context**: Explain why certain decisions were made if necessary.
6. **Optional**: Add TODOs if follow-up work is needed
7. **Complete**: Make sure everything you've done is included in the report, not the recent one, but the full conversation
8. **Track issue resolution**: solved issues from `/code-review` or the conversation go in `# Updates`; deferred issues go in `# Unsolved Issues`. Do not let either disappear from the project's record.
