---
session: 2026-09-24-codex-skill-compatibility (01a0c89a-35ee-7611-9189-a25de549876c)
---

# Codex skill installation and compatibility

# Description

Installed the 20 local dev-skills into Codex using symlinks, then adapted shared workflows while retaining Claude support. The user rejected a mandatory runtime-guide preamble repeated across every skill; the final implementation removes it and uses the shared session adapter added by later commits.

# Changes Made

- Removed the preamble from all 20 working-tree skills and made `references/agent-runtime.md` optional maintainer documentation. Most preambles were uncommitted; the committed find-session preamble is also removed.
- Kept task-specific session identity instructions in wrap-up, using `session-adapter.py show --json`, and documented cross-host search defaults. Preserved the later session-adapter, working-log, hook, and search implementations (`11c3ed6`, `252c57e`, `20ea85e`, `a9add2a`, `76276ef`).
- Adapted review model selection/concurrency and AGENTS.md evidence handling; repaired skill metadata and moved argument hints into body text. Claude renaming now requires an exact session ID and refuses direct Codex invocation; the shared adapter deliberately clears Codex environment variables for its Claude backend.
- Documented the local Codex install and existing backend capabilities. No hooks, MCP connections, or memory were installed by this session.

# Verification

Checks completed during implementation, not repeated as a Full wrap-up:

| Check | Expected and observed result |
|---|---|
| Skill creator `quick_validate.py` applied to every skill | All 20 metadata validations passed. |
| Scan every skill Markdown file for the runtime-guide dependency | No mandatory preamble or remaining reference dependency. |
| `bash -n skills/rename-session/rename.sh` | Shell syntax passed. |
| Rename helper with missing ID, nonexistent ID, Codex thread ID, or Codex session ID in a temporary HOME | Four refusals; the fixture transcript remained byte-identical. |
| Rename helper with explicit Claude ID and `test-title` | Appended the expected `custom-title` record to the exact fixture transcript. |
| `git diff --check` | Passed. |

No live Notion writes, deployment, multi-agent code review, or Full verification was performed. The script checks used temporary fixtures; cross-host production workflows were not end-to-end exercised here.

# Result

Installed symlinks expose the current shared skills without duplicate copies. Platform-specific behavior is handled by existing code adapters and task-local instructions, rather than requiring every skill to load a generic compatibility guide.

Quick wrap-up excludes the other session's create-tasks design-plan body changes, keep-awake script, and their reports. No applicable Notion configuration or deployment pipeline was found. Org-fork sync preflight was skipped because the shared checkout contains unrelated uncommitted work; the sync skill requires a clean checkout. Origin also has 11 locally unpushed commits from other sessions, so publishing this commit requires a separate push-scope decision.

# Attribution correction

A post-commit audit found later-session README capability additions and Quick-mode rename wording had been included in the first local commit. The unpublished commit was amended to exclude those hunks, retaining their working-tree bytes unchanged. The create-tasks design-plan body and keep-awake files remain excluded. No commits were pushed.

# Suggested Doc Updates

- Optionally replace machine-specific installation state in README with reproducible installation commands for other developers; propose-only in Quick mode.
- Historical session reports describe runtime-guide work as pending; preserve those dated observations and use this report for the final outcome.
