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
3. "Deploy" here (e.g. `/wrap-up` §9) = make the plugin cache match this clone. First run `diff -rq ~/.claude/plugins/cache/dev-skills/dev-skills/*/ <this repo>` (ignore `.git`). If there are no differences, deploy is done: the PostToolUse hook `bin/sync-to-plugin-cache.sh` already copied every Edit/Write under `skills/`. If there are differences (`bin/`, `shared/`, deleted files, or changes made through git or Bash), reinstall with `claude plugin marketplace update dev-skills && claude plugin update dev-skills@dev-skills`, then restart sessions. The marketplace is this directory, so the reinstall copies the **working tree**, other sessions' uncommitted edits included. Before confirming, list the differing files and the uncommitted files.