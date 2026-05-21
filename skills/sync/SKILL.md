---
name: sync
description: Start-of-day ritual for git-illiterate collaborators. Fetches the latest state, auto-merges upstream (current branch's tracked remote + origin/main + teammate branches updated in the last 24h) into the current branch, and pushes. If the working tree is dirty, defers to /wrap-up Quick to commit first. Any merge conflict aborts cleanly and tells the user to contact the reviewer. Use when the user says "開工", "sync", "start of day", "前置作業", "拉最新", "把對方的進度抓下來", or invokes /sync. Never runs destructive git commands (stash / reset --hard / checkout . / clean -fd / push --force / rebase).
---

# sync — start-of-day safety net

Two rules:

1. **Dirty tree → defer to `/wrap-up` Quick to commit first.** `/sync` itself never commits — only `/wrap-up` has the session context to write a meaningful commit + report.
2. **Clean tree → auto-merge everything upstream** (current branch's remote + origin/main + teammate branches updated in last 24h). Conflict-free only; any conflict aborts and refers to reviewer.

Speak 人話 — assume zero git literacy. Say 「拿到對方的最新進度」, not "fast-forward pull complete".

## Phase 0 — Pre-flight (parallel)

Short-circuit if any of these hit:

- Detached HEAD → stop, refer to reviewer.
- In-progress merge / rebase (`MERGE_HEAD`, `REBASE_HEAD`, `rebase-merge/`, `rebase-apply/` in git dir — worktree-aware via `git rev-parse --git-dir`) → stop, refer to reviewer.
- `index.lock` present → warn (another session may be active), continue.
- No `origin` remote → **local-only mode**: skip fetch / merge / push, just report local state and end.

Also capture: current branch, `git status --short --branch`.

## Phase 1 — Dirty tree handling

If clean, skip to Phase 2. Otherwise classify dirty paths against **session-edited files** (files this conversation touched):

- **Case A** dirty ⊆ session → 「你在這個 session 改了 X 個檔案還沒存。要直接跑 /wrap-up Quick 收尾嗎？」
- **Case B** mixed → 「session 改的 + 別處改的都在工作樹。要一起收尾嗎？（別處改動的 commit message 會比較生硬。）」
- **Case C** dirty ∩ session = ∅ → 「工作樹有改動但這個 session 沒動過。要直接收尾嗎？（commit message 會比較生硬。）」

All three: one `AskUserQuestion` popup, default = **Yes — 跑 /wrap-up Quick** (enter to confirm). On Yes, invoke `/wrap-up` with message _"from /sync — go straight to Quick mode, skip the Full/Quick popup"_, then continue to Phase 2. On No, end with 「OK，沒動 git。」

## Phase 2 — Fetch

`git fetch --all --prune`. Tell user 「正在抓最新狀態...」.

## Phase 3 — Auto-merge upstream (no popups)

All merges `--no-edit`. Run in order; any conflict at any sub-step → see Conflict handling below.

1. **Current branch's tracked upstream** — ff-only pull if behind; if diverged, merge `@{u}`.
2. **`origin/main`** — if not on main/master and main has commits HEAD lacks, merge.
3. **Teammate branches** — list remote branches updated in last 24h, exclude `origin/HEAD` / main / master / current branch / branches with nothing new, merge each (newest first). Tell user per branch: 「把對方的 \<branch\> 併進來...」.

### Conflict handling

Any merge conflict → `git merge --abort`, **stop the entire skill**, print:

```
✗ Merge conflict
  併入 <X> 時發生衝突。我不會解 conflict（99% 會解錯）。
  已完全還原。請聯絡 reviewer。
```

Never attempt `-X ours` / `-X theirs` / edit conflict markers / any auto-resolution.

## Phase 4 — Push

`git push` the merge commits (skip silently if nothing to push). On non-ff rejection: `git switch -c wip/<YYYYMMDD-HHMM>-<原branch>` → `git push -u origin HEAD` → 告訴使用者改推到 wip branch、請聯絡 reviewer.

## Phase 5 — Ready report (人話)

One block summary; omit empty groups; state no-ops explicitly:

```
✓ 同步完成
你在 branch: <name>
已併入: <upstream> / main / 對方 branches (或「沒新進度」)
已 push: 是 / 否
工作目錄: 乾淨，可以開工
```

## Guardrails — NEVER run

- `git stash` (any subcommand) — use `/wrap-up` Quick to commit + push instead.
- `git reset --hard` / `git reset --mixed <path>`.
- `git checkout .` / `git checkout -- <path>` / `git restore .` / `git restore --staged .` / `git restore --source ...`.
- `git clean -fd` / `-fdx` / `-fx`.
- `git push --force` / `-f` / `--force-with-lease`.
- `git rebase` (any flavor).
- Commits on `main` / `master` / `develop` (`/sync` shouldn't commit at all).
- Auto-resolving conflicts (`-X ours`, `-X theirs`, `--strategy ours`, editing markers).

## Out of scope

- No branch switching — stays on current branch.
- No worktree creation / recommendation.
- No auto-commit (Phase 1 hands off to `/wrap-up`).
- No PR creation (that's `/wrap-up` Full).
- No `/sync-report` or doc updates (those belong in `/wrap-up`).
