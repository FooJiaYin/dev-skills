# wrap-up — commit safety (shared by Full + Quick)

Universal commit hygiene. Wrapped by `./full.md` Step 7 and `./quick.md` Step 7 — each mode adds its own decisions (Full: Include report / Open PR / hand-written message; Quick: wip auto-message / always push).

## Pre-commit safety (parallel; stop on blocker)

- **Every repo this session wrote to, not just cwd.** Run `python3 ~/agent-skills/dev-skills/bin/session-log.py writes` — it lists this session's still-dirty files per repo from the session log's `[write]` lines (recorded at write time via git diff, so Bash/heredoc/`cp` writes are included and other sessions' files are not), and marks each as 「之後沒人動」 or 「之後被改」. Only if it says there is no session log (session predates 2026-09-17) fall back to collecting Write/Edit/write-Bash paths from the transcript. Then run this whole file per repo. Closing message gets one line per repo: `<repo>: <hash>` or `<repo>: 未 commit N 檔`; never print「完成」while any repo still holds this session's uncommitted files. (Seen: sibling repo `Poolgress_demo_` never checked, work sat uncommitted 9 days and blocked other sessions.)
- On `main` / `master` / `develop` → check if the project is main-direct first: count last 5 commits on the branch; if ≥3 landed directly on `main`/`master`/`develop` (no merge commits from feature branches), treat as main-direct and commit in place. Otherwise `git switch -c wip/<YYYYMMDD-HHMM>` and tell user 人話: 「你在 main 上，我先幫你開了一個暫存 branch」.
- Detached HEAD / `MERGE_HEAD` / `REBASE_HEAD` → stop, refer to reviewer.
- Files > 10MB → exclude from staging, warn user.
- **Multi-session: re-check `git branch --show-current` right before committing.** Another session can switch the branch under you between turns, so a branch you confirmed earlier (e.g. committed on `main` in an earlier step) may have changed (e.g. to `demo`) by the time you commit a follow-up — landing the commit on the wrong branch and separating a fix from the feature it fixes. If the current branch isn't the one you expect, stop and confirm with the user before committing.

## Smart staging (avoid `git add -A`)

**Scan the WHOLE staging list for foreign hunks in one pass, BEFORE the first `git add`.** Write out the full list of paths you intend to commit, then loop it — `for f in $LIST; do git diff -- "$f"; done` — and confirm every hunk is yours before staging anything. Do **not** derive the mixed-file set from "files I edited this session": a file you touched can also carry another session's uncommitted work, and a file you think is purely theirs can contain a one-line edit of yours. Checking iteratively (stage → grep the cached diff → find more → repeat) costs several rounds and risks committing foreign hunks in whichever round you stop at. Grep the *unstaged* diff for markers of the other work-in-progress (new identifiers, new column names, feature keywords) across the entire list at once.

Re-run `git status` / `git log -1` **fresh immediately before staging** — don't trust a session-start snapshot. In multi-session repos HEAD can advance underneath you (another agent/session commits mid-flow), which changes what's actually uncommitted, which files are already in HEAD, and which are genuinely mixed.

**Never a bare `git commit` in a shared-index repo.** `git add <file>` only *adds* — it does not scope the commit. A bare `git commit` commits the **entire index**, so if another session already `git add`ed its files, you'll bundle their in-flight work into your commit (with your message + session footer). Always: (a) `git diff --cached --name-only` immediately before committing to see everything currently staged, and (b) commit with an **explicit pathspec** — `git commit -m "…" -- <your-files>` (note: `-m` *before* `--`). This commits only your paths and leaves any other staged files staged for their author. If you already bundled (commit is local-only): `git reset --soft HEAD~1` then re-commit with the pathspec.

**Explicit pathspec does NOT protect a co-edited single file.** `git add <file>` stages the *whole* file, so if one file mixes your hunks + another session's **unstaged** hunks, `git commit -- <file>` still bundles theirs. Absence from `git diff --cached` only means no one **pre-staged** it — it does NOT mean the working tree is clean of another session's unstaged hunks. So **before `git add` on any file you didn't create this session, run `git diff <file>`** (unstaged, not just `--cached`) and confirm every hunk is yours. If you see hunks you didn't write → it's a co-edited file → use the technique below, not a plain `git add`.

**A `-` line you didn't write is foreign too.** It means HEAD is *ahead* of the working tree (another session committed via `hash-object` without writing the file back) — a plain `git add` silently reverts their commit. `git diff` also shows a *moved* block as delete+add, so check with `diff <(git show HEAD:<f> | sort) <(sort <f>) | grep '^<'`: every `<` line must be one you meant to change; otherwise rebuild from `git show HEAD:<f>` + your edits.

**Show the attribution table BEFORE asking any scope question.** When the tree holds work from more than one session, a "should I include X?" popup is unanswerable until the user knows whose each batch is — they will interrupt to ask 「到底是哪一個 session 未 commit」, and prose scattered across earlier turns does not count. Print one table first: batch → files → whose (evidence = the first `+`/`-` line of each file's diff), then ask. Fill "whose" from `find-session --touched <path>` (session uuid; it reads other sessions' `*.log.md` `[write]` lines first, jsonl only for pre-log sessions), **never** from a compaction summary or mtime — a summary once relabelled this session's own pre-compaction work as "another session's". ⚠️ CJK / non-ASCII filenames come back octal-escaped (`"docs/\351\276\215…"`) and silently fail to match in a `git diff --name-only | while read f` loop — use `git -c core.quotepath=false` for every status/diff you parse.

**Before committing, grep the docs for the paths you are about to commit.** A doc that says a file is 「尚未提交」/ untracked becomes wrong the instant you commit it (seen: `docs/schemas/index.md` warned that two migrations were uncommitted and that rebuilding from git would miss a column). Fix such statements in the SAME commit.

Stage deliberately. AskUserQuestion multi-select to confirm scope, especially for:

1. **Sensitive files** — `.env*`, `*.pem`, `*_rsa`, `*secret*`, `*credential*`, `*api*key*`, anything with API tokens. **Never stage even if user asks.**
2. **Temp / scratch files** — scratchpads (`findings.md`, `*-analysis.md`, `*-notes.md`, root `PLAN.md`), logs (`*.log`, `output.log`, `stderr.txt`), screenshots / recordings, one-off scripts at repo root, temp dirs (`tmp/`, `scratch/`, `playground/`), output data, downloads. Skip from staging; leave on disk (don't delete).
3. **Other session's work** — files dirty but not touched by this conversation's Edit / Write / Bash. Include with explicit user confirmation.

**Co-edited file (your hunks + another session's, no interactive `add -p`):** to commit ONLY your hunks from a file that also has another session's uncommitted changes, don't bundle theirs and don't lose them:

```bash
python3 ~/agent-skills/dev-skills/bin/session-log.py writes --mine <file> --stage
```

Every `[write]` line in the session log stores the file's blob before and after that one tool call (`pre=`/`sha=`, kept in the repo's `.git/objects`), so diff(pre, sha) is exactly your change and the other session's hunks — before, between or after yours — are never in it. The command rebuilds HEAD + your spans with `git merge-file`, prints the blob and stages it; the working file keeps the mixed content for the other author. Then commit with **no pathspec** — `git commit -- <file>` would re-read the working tree and bundle their hunks back in. ⚠️ A concurrent commit wipes `update-index` staging, so in a churning tree run `--mine --stage` and `git commit` in ONE chained `&&` call. If it reports conflicts, another session changed the same lines: resolve by hand, don't stage the blob. It refuses (with a reason) for writes recorded before 2026-09-18 or blobs pruned by `git gc` (~2 weeks) — only then fall back to the manual route: `cp <file> /tmp/<file>.full` → `git show HEAD:<file> > <file>` → re-apply only your edits → `git add` → commit → `cp /tmp/<file>.full <file>`.

Give suggestions for what to commit.

**Commit granularity — one commit per feature.** When the working set spans multiple distinct features/tasks (e.g. A venues + B billing + C predict), make ONE commit per feature, not a single bundled commit — even when committing them in the same pass. Bundled-then-split is expensive: once the combined commit is pushed (or another session builds on it) splitting it needs a force-push (forbidden in guarded repos). Stage + commit each feature's files separately from the start; ask if the boundaries are unclear.

**Verifying a commit landed.** `git log -10` shows topological order — your fresh commit can be buried under merged side-branches and look "missing". Authoritative checks before concluding it's lost: `git log -- <touched-file>` or `git merge-base --is-ancestor <sha> HEAD`.

## Session footer

Always end the commit message with a `Session: <name> (<id>)` footer line. Source: **id** = `$CLAUDE_CODE_SESSION_ID` (fallback: basename of the newest `~/.claude/projects/<encoded-cwd>/*.jsonl`); **name** = the title on line 1 of the session log (`session-log.py show | head -1`; it mirrors the latest `rename-session` title), falling back to the latest `customTitle` entry in the jsonl. If the name isn't set yet, fall back to the report/branch title. The PreToolUse footer hook denies a `git commit` that lacks this line and prints the exact footer to add.

When the work spans multiple sessions, list each pair comma-separated: `Session: feat-work (a1b2c3d4), bug-fix (e5f6g7h8)`.

## Push (with non-ff fallback)

- If `git log @{u}..HEAD` includes commits this session didn't make (another session's unpushed work), ask before pushing — a push publishes theirs too. Overrides Quick mode's "always push".
- `git push` (auto `-u origin HEAD` if no upstream).
- On non-ff rejection: `git switch -c wip/<YYYYMMDD-HHMM>-<original-branch>` → `git push -u origin HEAD` → tell user 人話: 「原 branch 跟 remote 分岔，存到 `wip/...`，請聯絡 reviewer」.
- **Never** `--force` / `--force-with-lease`.
