# wrap-up — Quick mode

Skips quality + deploy gates; ships report + safe commit + push only. For a time-constrained or git-illiterate collaborator, or when auto-invoked from `/sync`. Popup budget: 1–3 total (Step 6 staging + commit message, plus one Critical-finding popup from Step 2 only if there are Critical findings).

Steps in order:

| Step | Action |
|------|--------|
| 0 Scope | Silent — run `git diff --stat`; if >25 files / >2000 lines, append `⚠️ LARGE DIFF` hint to Step 6's commit message. |
| 1 Update docs | Invoke `/update-docs` with message: "Quick mode: propose-only, return markdown, skip edit." Capture output for Step 4. |
| 2 Quick review | Invoke `/quick-review` on this session's diff. Only **Critical** findings get one `AskUserQuestion` popup (fix / defer); everything else goes straight to `TODO.md`. No fix loop. |
| 3 Align | Invoke `/align end` non-interactively: no questions, ✗ items are written straight to `TODO.md`. |
| 4 Report | Invoke `/report` to write `docs/reports/YYYY-MM-DD-<title>.md`. Append `# Suggested Doc Updates` section with Step 1's propose markdown (skip section if empty). `TODO.md` is already covered by `/align end` (Step 3). |
| 5 Rename session | Invoke `rename-session` with the report title; it routes to the current host's supported helper. |
| 6 Commit + push | See below — includes auto-cleanup of safe cruft (`.DS_Store`, `*.swp`, `*~`, `.#*`, `*.orig`) before staging. |
| 7 Notion sync | If `AGENTS.md`/`CLAUDE.md` declares Notion URL AND Step 4 produced a report → **actually invoke `/sync-report`** — do NOT downgrade it to an "I can run it if you want" offer, and do NOT skip it for speed/quick-mode. Notion sync is independent of the push decision. Config may live in a **parent directory's** `AGENTS.md` (org-shared across sibling repos) — walk up to `$HOME` before deciding it's absent, and cross-check `grep -l "^notion:" docs/reports/*.md`: linked past reports mean the config exists somewhere you haven't looked. Skip ONLY when there's genuinely no Notion config / no report, or the user explicitly declines. Else skip silently. |
| 8 Deploy check | Detect CI/CD signals (`.github/workflows/*.yml` with a deploy job, `vercel.json`, `fly.toml` + workflow, `netlify.toml`, or docs saying "deploys automatically on merge"). If found → print「CI 會自動 deploy，跳過」. If not → print「沒偵測到 CI deploy，請手動 deploy 或請 reviewer 處理」. Never run a manual deploy command. |

## Step 6 — Safe commit + push

**Read `./commit.md` now (`cat` it) — do not commit from memory of it.** It holds the pre-commit safety checks, smart staging rules, the mandatory `Session: <name> (<id>)` footer, and the push fallback.

## Closing message (人話)

```
✓ Quick wrap-up 完成
- <repo>（<branch>）: <hash short> — <message first line>，已 push／未 push（原因）
- <other repo this session wrote to>: <hash> 或 未 commit N 檔（原因）
- report: docs/reports/<file>（含 # Suggested Doc Updates）
- quick-review: <N> 項發現（Critical <n>，其餘已進 TODO.md）
- 跳過: 測試 / 自動 deploy / improve
- 建議 reviewer 之後跑 `/wrap-up` Full 補上品質檢查
```

## Guardrails

- Never run `/verify`, `/code-review` (quick-review is the review here), or `/improve`.
- Never auto-edit docs — `/update-docs` is propose-only.
- Never delete outside the 5 safe patterns.
- Never `git add -A`, never `--force` push, never stage sensitive files even if user asks, never delete temp files (only skip from staging).
- If abnormal state (detached HEAD, MERGE_HEAD), stop and surface; do not recover.
