# wrap-up — Quick mode

Skips quality + deploy gates; ships report + safe commit + push only. For a time-constrained or git-illiterate collaborator, or when auto-invoked from `/sync`. Popup budget: 1–2 total (Step 7 staging + commit message).

Steps in order:

| Step | Action |
|------|--------|
| 0 Scope | Silent — run `git diff --stat`; if >25 files / >2000 lines, append `⚠️ LARGE DIFF` hint to Step 4's commit message. |
| 1 Update docs | Invoke `/update-docs` with message: "Quick mode: propose-only, return markdown, skip edit." Capture output for Step 2. |
| 2 Report | Invoke `/report` to write `docs/reports/YYYY-MM-DD-<title>.md`. Append `# Suggested Doc Updates` section with Step 1's propose markdown (skip section if empty). |
| 3 Rename session | Invoke `rename-session` skill with Step 2's report title. |
| 4 Commit + push | See below — includes auto-cleanup of safe cruft (`.DS_Store`, `*.swp`, `*~`, `.#*`, `*.orig`) before staging. |
| 5 Notion sync | If `AGENTS.md`/`CLAUDE.md` declares Notion URL AND Step 2 produced a report → invoke `/sync-report`. Else skip silently. |
| 6 Deploy check | Detect CI/CD signals (`.github/workflows/*.yml` with a deploy job, `vercel.json`, `fly.toml` + workflow, `netlify.toml`, or docs saying "deploys automatically on merge"). If found → print「CI 會自動 deploy，跳過」. If not → print「沒偵測到 CI deploy，請手動 deploy 或請 reviewer 處理」. Never run a manual deploy command. |

## Step 7 — Safe commit + push

Apply shared commit hygiene from `./commit.md` (pre-commit safety + smart staging + push fallback). Then Quick mode adds:

- **Default staging**: session-related files (touched by this conversation's Edit / Write / Bash). The shared multi-select popup still surfaces sensitive / temp / other-session for confirmation.
- **Commit message** — agent-generated, not hand-written:
  - Type = `wip:`. One-line summary from `git diff --staged` + session context. Footer: `[Quick wrap-up by Claude Code]` + session ID.
  - If Step 0 flagged large diff, include `⚠️ LARGE DIFF — 建議拆分` in body.
  - Popup to confirm: Use as-is (default) / Edit / Cancel.
- **Always push** after commit (no PR popup — partner doesn't open PRs). Use shared push fallback on non-ff.

## Closing message (人話)

```
✓ Quick wrap-up 完成
- branch: <name>
- commit: <hash short> — <message first line>
- 已 push 到 origin/<branch>
- report: docs/reports/<file>（含 # Suggested Doc Updates）
- 跳過: 測試 / code review / 自動 deploy / improve
- 建議 reviewer 之後跑 `/wrap-up` Full 補上品質檢查
```

## Guardrails

- Never run `/verify`, `/code-review`, or `/improve`.
- Never auto-edit docs — `/update-docs` is propose-only.
- Never delete outside the 5 safe patterns.
- Never `git add -A`, never `--force` push, never stage sensitive files even if user asks, never delete temp files (only skip from staging).
- If abnormal state (detached HEAD, MERGE_HEAD), stop and surface; do not recover.
