---
name: find-session
description: |
  Find Claude Code sessions (jsonl transcripts under ~/.claude/projects/) by topic
  keyword or by file-touch. Use whenever the user asks "which session…",
  "find the conversation where…", "who wrote this file", "when did we discuss X",
  "search my sessions for…", "搜 session", "find chat about…", or anything that
  requires looking up prior Claude Code conversations — even when the user doesn't
  explicitly say the word "session" but is clearly trying to recover prior chat
  context (e.g. "I remember we talked about Y, where was that?", "remind me where
  we set up Z"). Returns session UUIDs the user can paste into `claude --resume`.
---

# find-session

Search Claude Code session transcripts to recover prior conversations. Two query modes, three output formats, scope-escalation so you start narrow.

## When to invoke

- Topic recall — "find sessions discussing X", "where did we plan the auth refactor?"
- File-touch forensics — "which session wrote this file?", "who edited X?"
- Branch/fork mapping — "draw the graph of related sessions"

Don't invoke for: editor history / git history / external chat tools. This skill only sees Claude Code jsonl transcripts under `~/.claude/projects/`.

## How it works

Run [scripts/search.py](scripts/search.py). It walks `~/.claude/projects/<flattened-cwd>/*.jsonl` and (when escalated) other project folders, applies filters, and prints a ranked list.

### Default escalation

Always start with `--scope cwd` (current project only). If 0 results, retry with `--scope all` (every project except `.bak`). If still 0, retry with `--scope all-bak`. The `--escalate` flag does all three automatically.

```bash
python3 scripts/search.py --topic "spec skill" --escalate
```

Prefer escalation over jumping to `all` immediately — most queries are about the current project, and the noise from other projects (especially the `skill_listing` attachments that match every keyword) is real.

### Topic mode (`--topic`)

Matches the literal string (case-insensitive) against:
- User text and assistant text (with `<ide_opened_file>`, `<system-reminder>`, `<command-name|message|args>`, `<local-command-*>` wrappers stripped)
- `tool_use` input JSON (so a Bash command containing the term still matches)

**Critical filter** — sessions ship a system attachment of `type: skill_listing` containing every registered skill's description. A literal keyword from any skill description would otherwise match hundreds of unrelated sessions. The script skips these attachments.

### Touched-file mode (`--touched`)

Matches only sessions whose `tool_use` events (`Write` / `Edit` / `MultiEdit` / `NotebookEdit`) hit the given path. Use this to answer "who wrote X" definitively — text matches are unreliable because the file path appears in unrelated reads, listings, and grep output.

```bash
python3 scripts/search.py --touched ~/.claude/skills/spec/SKILL.md --escalate
```

If `--touched` returns 0 across all scopes, the file was likely written by hand outside Claude Code, not by a session.

### Combined

`--topic` and `--touched` AND together. Useful for "find the session that talked about *and* edited X".

### Output formats

- **compact** (default) — one line per session: `timestamp  uuid  first-user-msg`. Best for piping into `claude --resume`.
- **graph** — sorted by start time with fork detection via shared message-UUID overlap. Use when the user asks for relationships between sessions.
- **full** — per-session block with topic-match snippets, touch events, last 10 real user messages. Use for forensic "what did we actually discuss" questions.

```bash
python3 scripts/search.py --topic auth --output graph
python3 scripts/search.py --touched migrations/0042.sql --output full
```

### Other flags

- `--since YYYY-MM-DD` `--until YYYY-MM-DD` — date filter on session span
- `--limit N` — cap result count (0 = no limit)
- `--cwd PATH` — override the working directory used to compute the project folder (useful when running the skill from a different cwd than the project being searched)

## Result format & next step

The compact output looks like:

```
# scope=cwd  matches=4
2026-04-19T23:34:12  ed64209c-9eec-4e75-9034-ae237fc05102  I want to build a spec skill based on this. do you think it should…
2026-04-19T23:37:33  046818e9-856a-4ddd-af80-99a412b7dfc6  I want to build a spec skill based on this. do you think the spec…
2026-04-19T23:37:33  45af61c9-5bd1-48c8-aeeb-569295eb6f99  I want to build a spec skill based on this. do you think the spec…
2026-04-21T11:56:02  1a8058f5-beb5-4852-8dfd-6fba7989de42  review this plan
```

Tell the user they can resume any of those with `claude --resume <uuid>`. If the list is long, propose narrowing with `--touched`, a date range, or `--output graph` to see relationships.

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
python3 scripts/search.py --topic "spec skill" --escalate --output compact
```

**"Who actually wrote `~/.claude/skills/spec/SKILL.md`?"**
```bash
python3 scripts/search.py --touched ~/.claude/skills/spec/SKILL.md --escalate
# 0 results → tell the user the file was likely hand-edited outside Claude Code
```

**"Draw the branch graph of the spec-skill sessions"**
```bash
python3 scripts/search.py --topic "spec skill" --output graph --escalate
```

**"Find sessions from last week that touched the auth migration"**
```bash
python3 scripts/search.py --touched db/migrations/auth.sql --since 2026-05-07 --until 2026-05-13
```
