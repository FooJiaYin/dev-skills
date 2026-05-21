# wrap-up — commit safety (shared by Full + Quick)

Universal commit hygiene. Wrapped by `./full.md` Step 7 and `./quick.md` Step 7 — each mode adds its own decisions (Full: Include report / Open PR / hand-written message; Quick: wip auto-message / always push).

## Pre-commit safety (parallel; stop on blocker)

- On `main` / `master` / `develop` → `git switch -c wip/<YYYYMMDD-HHMM>` first, tell user 人話: 「你在 main 上，我先幫你開了一個暫存 branch」.
- Detached HEAD / `MERGE_HEAD` / `REBASE_HEAD` → stop, refer to reviewer.
- Files > 10MB → exclude from staging, warn user.

## Smart staging (avoid `git add -A`)

Stage deliberately. AskUserQuestion multi-select to confirm scope, especially for:

1. **Sensitive files** — `.env*`, `*.pem`, `*_rsa`, `*secret*`, `*credential*`, `*api*key*`, anything with API tokens. **Never stage even if user asks.**
2. **Temp / scratch files** — scratchpads (`findings.md`, `*-analysis.md`, `*-notes.md`, root `PLAN.md`), logs (`*.log`, `output.log`, `stderr.txt`), screenshots / recordings, one-off scripts at repo root, temp dirs (`tmp/`, `scratch/`, `playground/`), output data, downloads. Skip from staging; leave on disk (don't delete).
3. **Other session's work** — files dirty but not touched by this conversation's Edit / Write / Bash. Include with explicit user confirmation.

Give suggestions for what to commit.

## Push (with non-ff fallback)

- `git push` (auto `-u origin HEAD` if no upstream).
- On non-ff rejection: `git switch -c wip/<YYYYMMDD-HHMM>-<original-branch>` → `git push -u origin HEAD` → tell user 人話: 「原 branch 跟 remote 分岔，存到 `wip/...`，請聯絡 reviewer」.
- **Never** `--force` / `--force-with-lease`.
