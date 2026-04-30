---
name: report
description: Analyze the current chat conversation, file changes, and actions taken to create a comprehensive report. Saves to docs/reports/YYYY-MM-DD-[title].md
argument-hint: "[optional title]"
---

Analyze the current chat conversation, file changes, and actions taken to create a comprehensive report using the specified template.

Save the report as `docs/reports/YYYY-MM-DD-[title].md`

The date should be the date when the task is mainly worked on, not the date when the report is generated.

## Report Generation Process

1. **Analyze Chat History**: Review the conversation to capture only the core issue, discussion points and decisions made, solutions attempted and their outcomes
2. **Examine File Changes**: Mention only relevant changes and the main purpose of the changes
3. **Summarize Actions Taken**: commands executed, deployments, or test runs

## Available Report Templates

Please choose a template to follow:

1. Task Report: (`./templates/report-task.md`)
2. Bug Fix Report: (`./templates/report-bug-fix.md`)
3. Planning Report: (`./templates/report-planning.md`) — for brainstorming, design discussions, trade-off analysis, decision records. May cover multiple related topics. **STRONG DEFAULT: raw conversation paste per topic.** Only upgrade a topic to the structured form (Discussion / Solutions / Decision) when the topic spanned **7 or more conversation turns** (back-and-forth exchanges on the same topic). A short topic stays as raw paste even if it contains a decision, compared options, or discussed trade-offs. Decide per topic when first drafting it — don't switch modes mid-topic. Mixed modes across topics in one report are fine.

## Multiple Reports

If the conversation covers multiple **unrelated** tasks (e.g. designing a framework AND building a CLI tool), ask the user whether to split into separate reports before writing. Each report should be a self-contained document with its own title and file.

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
2. Run: `bash ~/.claude/skills/report/attach-plan.sh <mode> <plan-file> <report-file>`
   - `<mode>` is `prepend` for Task / Bug Fix reports, `append` for Planning reports

Do NOT read the plan file yourself. The script handles everything.
If no plan was used, skip this step.

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
