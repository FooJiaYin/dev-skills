---
name: quick-review
description: Lightweight review run at the end of EVERY session/commit — invoked by /wrap-up (Full and Quick). `codex review` on this session's uncommitted diff (cross-model), then resumes the same Codex thread with the shared review commons so the checklist doesn't anchor the first pass. Writes REVIEW.md. For a whole branch before merge, a big refactor, or an architecture audit, use code-review.
---

**Arguments:** `[--files <path> ...] [--base <ref>]`

Two-round review of this session's diff. The deterministic part lives in `run.py`; this file covers only the judgment calls.

## Steps

1. **Scope.** If the working tree holds other sessions' changes too, pass only this session's files (wrap-up supplies the list): `--files a.ts b.ts`. If the session already committed its work, pass `--base <parent of the session's first commit>` so those commits are reviewed too. Otherwise pass nothing and the whole uncommitted diff is reviewed.

2. **Run** from inside the repo:

   ```bash
   python3 <dev-skills-root>/skills/quick-review/run.py [--files ...]
   ```

   It runs `gitleaks` if installed (else `secret_scan: skipped`), round 1 `codex exec review --uncommitted` with no checklist, names the Codex thread `quick-review ← <session title> (<id8>)`, round 2 resumes that thread with [`shared/review/commons.md`](../../shared/review/commons.md) plus the repo's `docs/review-standard.md` and asks only for new findings, then writes `REVIEW.md` at the repo root (git-ignored) and prints a one-line summary. Codex takes minutes; run it in the foreground with a long timeout (up to 30 min).

3. **Read the result.** Relay the summary line. `REVIEW.md` has `General findings` (round 1) and `Checklist findings` (round 2), plus `Secret scan` when gitleaks matched on a changed line. Severity: P0/P1 → Critical, P2 → Warning, P3 → Suggestion. The caller (wrap-up) owns the fix / defer decision.
   - If `REVIEW.md` belongs to another session (its `session:` differs), `run.py` writes `REVIEW-<id8>.md` instead; read that one.
   - **Exit code 4 / `status: incomplete`**: round 2 (the checklist) didn't run. Tell the user, and run the fallback's steps 1–3 for round 2 only, or say the review is incomplete. Never report it as clean.

## Fallback — exit code 3

`run.py` exits 3 and prints `FALLBACK:` when `codex` is missing, the review call fails, or you are running on a Codex host (a Codex review of Codex work is not cross-model). Then:

Pass the same `--files` / `--base` to every `run.py` call below.

1. Spawn **one** reviewer agent (Claude: `sonnet`; Codex: inherit). Brief: review the diff (`git diff <base>` when a base is given; otherwise `git diff --cached` + `git diff` + untracked files, limited to the `--files` list if given) with its own judgment, report each finding as `- [P0-P3] <title> — <path>:<line>` followed by an indented body, nothing else. Save its reply to `<scratchpad>/round1.txt` (absolute path).
2. `SendMessage` the same agent the output of `run.py --print-prompt [--files ...]` (commons + project standard + "only new findings"). Save the reply to `<scratchpad>/round2.txt`.
3. `python3 <dev-skills-root>/skills/quick-review/run.py --from-text <scratchpad>/round1.txt <scratchpad>/round2.txt [--files ...]` — writes `REVIEW.md` with `engine: agent`.

## Rules

- Read-only: never edit source files. Only `REVIEW.md` (or `REVIEW-<id8>.md`) and `.gitignore` are written.
- Needs the repo-level `shared/review/commons.md` (install the whole dev-skills plugin, not this folder alone). Without it, round 2 runs on the project standard plus a minimal security pass and logs a warning.
- Don't run typecheck, lint or tests — that is `/verify`'s job.
- Don't spawn other agents, except the single fallback reviewer.
- A failed thread rename never fails the review.
