# wrap-up — commit safety (shared by Full + Quick)

Universal commit hygiene. Wrapped by `./full.md` Step 7 and `./quick.md` Step 7 — each mode adds its own decisions (Full: Include report / Open PR / hand-written message; Quick: wip auto-message / always push).

## Pre-commit safety (parallel; stop on blocker)

- On `main` / `master` / `develop` → check if the project is main-direct first: count last 5 commits on the branch; if ≥3 landed directly on `main`/`master`/`develop` (no merge commits from feature branches), treat as main-direct and commit in place. Otherwise `git switch -c wip/<YYYYMMDD-HHMM>` and tell user 人話: 「你在 main 上，我先幫你開了一個暫存 branch」.
- Detached HEAD / `MERGE_HEAD` / `REBASE_HEAD` → stop, refer to reviewer.
- Files > 10MB → exclude from staging, warn user.
- **Multi-session: re-check `git branch --show-current` right before committing.** Another session can switch the branch under you between turns, so a branch you confirmed earlier (e.g. committed on `main` in an earlier step) may have changed (e.g. to `demo`) by the time you commit a follow-up — landing the commit on the wrong branch and separating a fix from the feature it fixes. If the current branch isn't the one you expect, stop and confirm with the user before committing.

## Smart staging (avoid `git add -A`)

Re-run `git status` / `git log -1` **fresh immediately before staging** — don't trust a session-start snapshot. In multi-session repos HEAD can advance underneath you (another agent/session commits mid-flow), which changes what's actually uncommitted, which files are already in HEAD, and which are genuinely mixed.

**Never a bare `git commit` in a shared-index repo.** `git add <file>` only *adds* — it does not scope the commit. A bare `git commit` commits the **entire index**, so if another session already `git add`ed its files, you'll bundle their in-flight work into your commit (with your message + session footer). Always: (a) `git diff --cached --name-only` immediately before committing to see everything currently staged, and (b) commit with an **explicit pathspec** — `git commit -m "…" -- <your-files>` (note: `-m` *before* `--`). This commits only your paths and leaves any other staged files staged for their author. If you already bundled (commit is local-only): `git reset --soft HEAD~1` then re-commit with the pathspec.

**Explicit pathspec does NOT protect a co-edited single file.** `git add <file>` stages the *whole* file, so if one file mixes your hunks + another session's **unstaged** hunks, `git commit -- <file>` still bundles theirs. Absence from `git diff --cached` only means no one **pre-staged** it — it does NOT mean the working tree is clean of another session's unstaged hunks. So **before `git add` on any file you didn't create this session, run `git diff <file>`** (unstaged, not just `--cached`) and confirm every hunk is yours. If you see hunks you didn't write → it's a co-edited file → use the technique below, not a plain `git add`.

Stage deliberately. AskUserQuestion multi-select to confirm scope, especially for:

1. **Sensitive files** — `.env*`, `*.pem`, `*_rsa`, `*secret*`, `*credential*`, `*api*key*`, anything with API tokens. **Never stage even if user asks.**
2. **Temp / scratch files** — scratchpads (`findings.md`, `*-analysis.md`, `*-notes.md`, root `PLAN.md`), logs (`*.log`, `output.log`, `stderr.txt`), screenshots / recordings, one-off scripts at repo root, temp dirs (`tmp/`, `scratch/`, `playground/`), output data, downloads. Skip from staging; leave on disk (don't delete).
3. **Other session's work** — files dirty but not touched by this conversation's Edit / Write / Bash. Include with explicit user confirmation.

**Co-edited file (your hunks + another session's, no interactive `add -p`):** to commit ONLY your hunks from a file that also has another session's uncommitted changes, don't bundle theirs and don't lose them:
1. `cp <file> /tmp/<file>.full` — back up the mixed working tree.
2. `git show HEAD:<file> > <file>` — reset the working file to HEAD (read-only git + redirect; **not** `checkout`/`restore`).
3. Re-apply only *your* edits (same Edit old/new strings; verify each anchor still exists in HEAD first).
4. `git add <file>` → commit. The staged diff = HEAD + your hunks only (scan it for the other session's markers to confirm clean).
5. `cp /tmp/<file>.full <file>` — restore the mixed version; their hunks return as uncommitted, ready for their author.

**Working-tree-free variant (another session editing the same file, or HEAD moving mid-commit):** stage the temp blob directly — `H=$(git hash-object -w /tmp/t); git update-index --cacheinfo 100644,$H,<file>` — never resets the working file. ⚠️ A concurrent commit wipes your `update-index` staging, so in a churning tree re-stage + commit in ONE chained `&&` call.

Give suggestions for what to commit.

**Commit granularity — one commit per feature.** When the working set spans multiple distinct features/tasks (e.g. A venues + B billing + C predict), make ONE commit per feature, not a single bundled commit — even when committing them in the same pass. Bundled-then-split is expensive: once the combined commit is pushed (or another session builds on it) splitting it needs a force-push (forbidden in guarded repos). Stage + commit each feature's files separately from the start; ask if the boundaries are unclear.

**Verifying a commit landed.** `git log -10` shows topological order — your fresh commit can be buried under merged side-branches and look "missing". Authoritative checks before concluding it's lost: `git log -- <touched-file>` or `git merge-base --is-ancestor <sha> HEAD`.

## Session footer

Always end the commit message with a `Session: <name> (<id>)` footer line. Source: **id** = `$CLAUDE_CODE_SESSION_ID` (fallback: basename of the newest `~/.claude/projects/<encoded-cwd>/*.jsonl`); **name** = the latest `customTitle` entry in that session's jsonl (the title `rename-session` writes). If the name isn't set yet, fall back to the report/branch title.

When the work spans multiple sessions, list each pair comma-separated: `Session: feat-work (a1b2c3d4), bug-fix (e5f6g7h8)`.

## Push (with non-ff fallback)

- `git push` (auto `-u origin HEAD` if no upstream).
- On non-ff rejection: `git switch -c wip/<YYYYMMDD-HHMM>-<original-branch>` → `git push -u origin HEAD` → tell user 人話: 「原 branch 跟 remote 分岔，存到 `wip/...`，請聯絡 reviewer」.
- **Never** `--force` / `--force-with-lease`.
