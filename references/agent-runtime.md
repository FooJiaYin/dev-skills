# Agent runtime compatibility

Optional maintainer reference for host differences, not an execution prerequisite.
Keep executable host differences in `bin/session-adapter.py` and its backends;
keep task-specific instructions in the skill that uses them. Normal skills do
not need to load this document. The host already supplies tool contracts,
permissions, and instruction precedence.

## Tools and interaction

- Determine the host from the current session, not from the presence of a
  `.claude` directory. A repository can support both agents.
- `Read`, `Write`, `Edit`, `Bash`, and `Task`/`Agent` describe capabilities.
  In Codex use its available file/shell tools, `apply_patch`, and delegation tools.
  Resolve helper paths relative to the real skill directory (follow symlinks),
  and set the shell working directory explicitly to the target project.
- `/skill-name` means load and follow the installed skill. In Codex it can be
  invoked as `$skill-name`; do not execute slash commands in a shell.
- `AskUserQuestion` means obtain the relevant user input. In Codex use an
  available question tool only where its contract allows; otherwise ask in chat.
  For required approval, wait for an explicit answer. Do not interpret a timeout
  or preselected option as consent. Existing explicit authorization carries over;
  a skill's popup wording does not require re-approval of the same action.
  Shell sandbox escalation uses the shell tool's approval mechanism.
- `EnterPlanMode`/`ExitPlanMode` and numbered Claude plan phases apply only where
  the host exposes them. In Codex use the current collaboration mode and present
  a concrete plan in chat or the requested file. Do not invent mode-changing tools.
- Use the actual available MCP tool schemas. A name like `notion-fetch` denotes
  an operation, not a guaranteed namespace or argument shape. Discover its
  equivalent and inspect the schema before calling it. If a connection is absent,
  finish independent local work and report the external step as blocked. Do not
  fabricate successful syncs or silently substitute a different service.
- Claude's `~/.claude/memory/notion-me.md` may be read as an existing identity
  hint; verify it against the connected workspace. In Codex, do not create or
  update Claude's memory implicitly. Ask for missing identity only when needed.

## Instructions, models, and agents

- Read applicable `AGENTS.md` guidance, with `CLAUDE.md` as the compatibility
  source where applicable. Deduplicate symlinks and respect directory scope.
- In Codex, personal instruction changes belong in `$CODEX_HOME/AGENTS.md`
  (normally `~/.codex/AGENTS.md`); project facts belong in repository docs.
  Persist preferences only when authorized, using the host's supported mechanism.
- Claude model names such as Haiku/Sonnet are Claude-specific choices. In Codex
  inherit the parent model unless the user or applicable instructions choose an
  available model. Never pass a Claude model slug to Codex.
- Delegate only where authorized and available. Honor concurrency limits: process
  a large fan-out in bounded batches. Do not restart user-interrupted agents
  automatically. If delegation is unavailable, perform the review passes locally
  and disclose the lack of independent reviewers; do not claim agents ran.

## Plans and session evidence

- Prefer the plan explicitly used in this conversation, then the project's
  `docs/plans/` or task files. Claude's `~/.claude/plans/` is a Claude-only fallback;
  modification time alone does not identify the current task's plan.
- In Codex, derive changed-file scope from this conversation's tool results and
  fresh Git diffs across each repo touched. A dirty file or its mtime is not proof
  of authorship. Mark attribution unknown when evidence is missing.
- `report/export-transcript.py` and `rename.sh` operate on Claude sessions;
  use `session-adapter.py` for Codex. `session-log.py` CLI operations now dispatch
  to Codex when its ID is exposed; its JSON hook commands remain Claude-specific.
  Use `find-session --host claude` when explicitly investigating Claude history.
- Codex working logs: `bin/session-adapter.py log --open` refreshes and opens a
  derived `.log.md` under `$CODEX_HOME/dev-skills/session-logs/`. `--watch` refreshes
  while running; configured Codex lifecycle hooks refresh automatically after
  they are trusted in `/hooks`. `--note` preserves local notes.
  `find-session --host codex --open-id current` opens the current log; topic/file
  searches use app-server history. Completed `fileChange` events are evidence,
  but shell writes and Claude pre/post snapshots/hunk attribution are not covered.
- Codex session identity comes from an ID explicitly exposed by the host (for
  example `CODEX_THREAD_ID` when present), never the newest Claude transcript.
  Use the report/task title for the name. Preserve `Session: <title> (<id>)` in
  commit messages and `session:` in reports. If no ID is exposed, use the honest
  marker `codex-id-unavailable`; it is not a resumable session identifier.
- Session renaming: run `python3 <dev-skills-root>/bin/session-adapter.py rename
  '<title>'`. It calls app-server `thread/name/set` and verifies with
  `thread/read`; never write directly to Codex SQLite or rollout files. If the
  sandbox blocks app-server state initialization under `~/.codex`, request the
  host's normal filesystem approval and retry once.
- Session transcript export: run `python3
  <dev-skills-root>/bin/session-adapter.py export [--full] [-o PATH]`. It reads the
  explicit current thread ID and pages through app-server turns. Do not substitute
  Claude's JSONL helpers or reconstruct a supposedly complete transcript from
  visible chat context.
- Installing these skills does not install hooks, memory, MCP connections, or
  session logging. Do not assume those facilities are active.
