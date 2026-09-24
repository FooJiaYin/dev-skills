---
name: find-session
description: |
  Find and open Claude Code or Codex session history by topic or edited file.
  Use for "find the conversation where…", "who wrote this file", "搜 session",
  "open this session log", or recovering earlier development decisions.
  Searches Claude and Codex together by default, with an explicit --host filter.
---

Read [agent runtime compatibility](../../references/agent-runtime.md) before executing this skill; its platform mappings also apply to the steps below.

# find-session

Search both Claude and Codex by default (`--host all`); use `--host claude` or
`--host codex` to restrict the source. Combined results are labeled by host,
numbered, and sorted newest first. `--limit` applies to the merged list and
`--open N` opens that list's N-th result using the correct backend.
With `--escalate`, search both sources within cwd first, then expand together
through all and all-bak only if neither source matches. Try literal then all-word
matching within each scope. A backend failure still prints available results,
but reports an incomplete search and exits 2.
`--open-id current` uses the active host's explicit session ID. Other IDs/prefixes
are resolved across both sources; ambiguous IDs require `--host` or a longer ID.
Resume with `claude --resume <ID>` or `codex resume <ID>` as labeled.
Do not infer the current session from whichever log was modified most recently.

Example combined search:

```bash
python3 scripts/search.py --topic "workflow inventory" --escalate
python3 scripts/search.py --touched docs/PRD.md --limit 10 --open 2
```

## Codex logs and search

Use the same `scripts/search.py` entrypoint:

```bash
python3 scripts/search.py --host codex --open-id current
python3 scripts/search.py --host codex --open-id <ID-or-unique-prefix>
python3 scripts/search.py --host codex --topic "workflow inventory" --escalate --open
python3 scripts/search.py --host codex --touched docs/PRD.md --output full
```

Opening generates/refreshes the session's working log and opens it in the editor.
Codex reads `thread/list`, `thread/read`, and `thread/turns/list` through app-server;
it does not parse native rollouts or directly edit SQLite. If sandboxing blocks
app-server state access or the editor, use the host's normal escalation mechanism.

- Logs live at `$CODEX_HOME/dev-skills/session-logs/<project-hash>/<id>.log.md`
  (`CODEX_HOME` defaults to `~/.codex`). They contain conversation text, abbreviated
  tool activity, completed file changes, errors, and compaction markers.
- `bin/session-adapter.py log --open` refreshes the current log. Add `--watch` to
  refresh every 15 seconds while that command runs; stop with Ctrl-C. Codex
  lifecycle hooks may refresh automatically after `/hooks` trust review; see
  [hook setup](../../docs/hooks-codex-session-log.md). `--note "text"` saves local notes
  separately so refreshing preserves them. These are derived views, not native logs.
- `bin/session-log.py show|note|writes|export|backfill` dispatches to Codex when
  its session ID is exposed. `writes` shows completed `fileChange` evidence only;
  `backfill` accepts one ID or the current session. Claude `--mine`/`--stage`,
  write snapshots, and hook injection are not supported for Codex.
- Search starts at the current project, then all projects with `--escalate`.
  Active and archived interactive threads are included; `all-bak` is equivalent
  to `all` for Codex. It excludes the current session from search results.
- Topics search titles, user/assistant text and tool inputs; multiword queries
  fall back to requiring all words within each scope. `--since`/`--until` filter
  the session span inclusively, and results are newest first.
- `--touched` requires a completed `fileChange` event, including rename paths.
  Shell/MCP writes without that event cannot be attributed; zero matches do not
  establish that a file was edited by hand. Mentioning or reading a file is not a write.
- `--output graph` reports the API's `forkedFromId` when available; it does not
  infer forks from timestamps. Unreadable threads are reported as an incomplete
  search (exit 2), not silently counted as no match.
- Resume a result with `codex resume <ID>`. Log output applies the existing
  credential-pattern redactor; this is best-effort, not a guarantee for sharing.

## Claude history

Claude history still uses `~/.claude/projects/` and the existing hook-generated
`.log.md` files. Pass `--host claude` to search only Claude from either host. The
remaining instructions describe this backend.

## When to invoke

- Topic recall — "find sessions discussing X", "where did we plan the auth refactor?"
- File-touch forensics — "which session wrote this file?", "who edited X?"
- Branch/fork mapping — "draw the graph of related sessions"

Don't use session search as a substitute for git/editor history or external chat tools.

## How it works

Run [scripts/search.py](scripts/search.py). It walks `~/.claude/projects/<flattened-cwd>/*.jsonl` and (when escalated) other project folders, applies filters, and prints a ranked list.

Sessions started on/after 2026-09-17 also have a `<sid>.log.md` next to the jsonl (the session log written by `dev-skills/bin/session-log.py`). The script scans that instead when present: ~100× smaller, and its `[write]` lines are exact (recorded at write time), so `--touched` answers are definitive for those sessions. Older sessions still go through the jsonl.

### Default escalation

Always start with `--scope cwd` (current project only). If 0 results, retry with `--scope all` (every project except `.bak`). If still 0, retry with `--scope all-bak`. The `--escalate` flag does all three automatically.

```bash
python3 scripts/search.py --host claude --topic "spec skill" --escalate
```

Prefer escalation over jumping to `all` immediately — most queries are about the current project, and the noise from other projects (especially the `skill_listing` attachments that match every keyword) is real.

### Topic mode (`--topic`)

Matches the literal string (case-insensitive) against:
- User text and assistant text (with `<ide_opened_file>`, `<system-reminder>`, `<command-name|message|args>`, `<local-command-*>` wrappers stripped)
- `tool_use` input JSON (so a Bash command containing the term still matches)

A multi-word topic is tried as a literal phrase first; if nothing matches, the script retries requiring **every word** (AND) and prints a `# no literal match …` line. The session running the search is always excluded (it matches its own query).

**Critical filter** — sessions ship a system attachment of `type: skill_listing` containing every registered skill's description. A literal keyword from any skill description would otherwise match hundreds of unrelated sessions. The script skips these attachments.

### Touched-file mode (`--touched`)

Matches only sessions whose `tool_use` events (`Write` / `Edit` / `MultiEdit` / `NotebookEdit`) hit the given path. Use this to answer "who wrote X" definitively — text matches are unreliable because the file path appears in unrelated reads, listings, and grep output.

```bash
python3 scripts/search.py --host claude --touched ~/.claude/skills/spec/SKILL.md --escalate
```

If `--touched` returns 0 across all scopes, report that no write evidence was found. Shell writes and missing history can also explain the absence.

### Combined

`--topic` and `--touched` AND together. Useful for "find the session that talked about *and* edited X".

### Output formats

- **compact** (default) — one line per session: `timestamp  uuid  log|-  first-user-msg` (`log` = has a session log you can `--open`). Best for piping into `claude --resume`.
- **graph** — sorted by start time with fork detection via shared message-UUID overlap. Use when the user asks for relationships between sessions.
- **full** — per-session block with topic-match snippets, touch events, last 10 real user messages. Use for forensic "what did we actually discuss" questions.

```bash
python3 scripts/search.py --host claude --topic auth --output graph
python3 scripts/search.py --host claude --touched migrations/0042.sql --output full
```

### Other flags

- `--since YYYY-MM-DD` `--until YYYY-MM-DD` — date filter on session span
- `--limit N` — cap result count (0 = no limit)
- `--cwd PATH` — override the working directory used to compute the project folder (useful when running the skill from a different cwd than the project being searched)
- `--open [N]` — after the search, open the N-th hit's `<sid>.log.md` in the editor (default 1). `--open-id <uuid>` opens a known session's log without searching (id prefix is enough). Use these whenever the user wants to *read* a session's log (「開 log」「我要看那個 session 的紀錄」「打開第二個」) — the file lives under the hidden `~/.claude/projects/` tree and is awkward to reach by hand. Sessions before 2026-09-17 have no log; the script says so and prints the jsonl path instead.

## Result format & next step

The compact output looks like:

```
# scope=cwd  matches=4
2026-04-19T23:34:12  ed64209c-9eec-4e75-9034-ae237fc05102  -    I want to build a spec skill based on this. do you think it should…
2026-04-19T23:37:33  046818e9-856a-4ddd-af80-99a412b7dfc6  -    I want to build a spec skill based on this. do you think the spec…
2026-04-19T23:37:33  45af61c9-5bd1-48c8-aeeb-569295eb6f99  -    I want to build a spec skill based on this. do you think the spec…
2026-09-17T00:19:04  9f0295b0-6a7f-461a-8d7a-ed85f717c124  log  我覺得他不懂我要什麼
```

Tell the user they can resume any of those with `claude --resume <uuid>`, and open a `log` row with `--open N`. If the list is long, propose narrowing with `--touched`, a date range, or `--output graph` to see relationships.

## Pitfalls to surface to the user

These are real false-positive sources — call them out when relevant:

- **`skill_listing` attachments** — already filtered, but if a topic search still returns surprisingly many hits across unrelated projects, double-check the matches aren't all in skill metadata. The full output's snippet field makes this obvious.
- **`tool_result` user turns** — these are tool replies, not real user messages. Filtered out of the "first user msg" / "last N user msgs" fields, but they can still contribute to topic matches via assistant text that quoted them.
- **`.bak` project folders** — duplicate sessions from old project paths. The script de-dupes by session UUID across folders, so each session shows once even if it lives in both `-Users-foo-bar` and `-Users-foo-bar.bak`.
- **Forks aren't always real forks** — three sessions that opened the same file at the same second can look like a fork but share zero message UUIDs. The graph output uses UUID overlap, not timestamp proximity, to call something a fork.
- **Sessions don't always represent execution** — a session can contain plans, ExitPlanMode, and discussion without ever writing a file. If `--topic` finds a session but `--touched` doesn't, that's a discussion-only session.

## Examples

**"Find /spec skill design discussions"**
```bash
python3 scripts/search.py --host claude --topic "spec skill" --escalate --output compact
```

**"Who actually wrote `~/.claude/skills/spec/SKILL.md`?"**
```bash
python3 scripts/search.py --host claude --touched ~/.claude/skills/spec/SKILL.md --escalate
# 0 results → report no write evidence; do not infer authorship
```

**"Draw the branch graph of the spec-skill sessions"**
```bash
python3 scripts/search.py --host claude --topic "spec skill" --output graph --escalate
```

**"Find sessions from last week that touched the auth migration"**
```bash
python3 scripts/search.py --host claude --touched db/migrations/auth.sql --since 2026-05-07 --until 2026-05-13
```
