## Python
1. Before running python code, check if virtual environment (`env`/`.venv`) exists
2. If exists, `source .venv/bin/activate` (Linux/Mac) or `source .venv/Scripts/activate` (Windows)

## Node.js
1. Use `yarn` instead of `npm`, unless `pnpm` is specified

## Documentation
1. Use `docs` folder for documentation files
2. Use `AGENTS.md` for agent-related documentation, instead of `CLAUDE.md`, `CURSOR.md`, etc. Add symlink of `AGENTS.md` as `CLAUDE.md` for backward compatibility but prefer `AGENTS.md` for all updates.

## Skills
1. When writing a skill from a plan or discussion, list every agreed item as in-skill or deferred (with where it's tracked) before calling it done.
2. Adding or renaming a skill: update the README skill table and the `<skill-name>` install list in the same commit.
3. Every skill change: check and state where it runs — (a) Codex, (b) another machine (no hard-coded user paths; hooks it relies on are in the repo's setup docs, not only in one `~/.claude/settings.json`), (c) another OS. Anything host- or OS-specific (`~/.claude/…` files, macOS-only commands such as `top -l` / `sysctl vm.*`, Homebrew paths) must skip cleanly and say so — never crash, and never print an empty result that reads as "nothing found". Put a one-line `Runs on:` note in the SKILL.md and the same three answers in the report. (Seen 2026-11-19: `cleanup-processes` and the `[agent]` session-log hook were written for this Mac + Claude Code only; the user asked 「預計在codex上可以跑嗎？換台電腦和OS可以跑嗎？每次改skill要檢查這個」.)
4. "Deploy" here (e.g. `/wrap-up` §9) = make the plugin cache match this clone. First run `diff -rq <installPath> <this repo>` (ignore `.git`). Take `installPath` from the `dev-skills@dev-skills` entry in `~/.claude/plugins/installed_plugins.json`; older version folders in the cache are stale. If there are no differences, deploy is done: the PostToolUse hook `bin/sync-to-plugin-cache.sh` already copied every Edit/Write under `skills/`. If there are differences (`bin/`, `shared/`, deleted files, or changes made through git or Bash), run `claude plugin marketplace update dev-skills`, then `/reload-plugins` or start a new session. `claude plugin update` reports "nothing to update" for this directory marketplace, because the folder is read at session start. The marketplace is this directory, so the reinstall copies the **working tree**, other sessions' uncommitted edits included. Before confirming, list the differing files and the uncommitted files.