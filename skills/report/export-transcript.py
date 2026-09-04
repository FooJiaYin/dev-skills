#!/usr/bin/env python3
"""Export a Claude Code conversation (jsonl transcript) to a markdown file.

Usage:
  export-transcript.py                          # current session -> docs/reports/<date>-<slug>-transcript.md
  export-transcript.py --full                   # include thinking, tool calls, tool results
  export-transcript.py -o notes.md              # explicit output path
  export-transcript.py --session <uuid|path>    # some other session
  export-transcript.py --stdout                 # print instead of writing
  export-transcript.py --since 2026-08-19T05:00 # only turns at/after this timestamp

Session resolution order: --session > $CLAUDE_CODE_SESSION_ID > newest *.jsonl in
the cwd's ~/.claude/projects/<flattened-cwd>/ folder.

Default output is the readable dialogue only: user prompts + assistant prose.
Thinking blocks, tool calls, tool results, IDE wrappers and system-reminders are
dropped. `--full` adds them back.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECTS_ROOT = Path.home() / ".claude" / "projects"

# Noise wrappers: dropped from rendered text entirely.
WRAPPERS = [
    re.compile(r"<ide_opened_file>.*?</ide_opened_file>", re.S),
    re.compile(r"<ide_selection>.*?</ide_selection>", re.S),
    re.compile(r"<system-reminder>.*?</system-reminder>", re.S),
    re.compile(r"<local-command-stdout>.*?</local-command-stdout>", re.S),
    re.compile(r"<local-command-caveat>.*?</local-command-caveat>", re.S),
    re.compile(r"<command-message>.*?</command-message>", re.S),
]
# Slash-command invocations are kept, rewritten as a literal `/name args` line,
# so a `/report`-style turn doesn't vanish from the transcript.
RX_CMD_NAME = re.compile(r"<command-name>(.*?)</command-name>", re.S)
RX_CMD_ARGS = re.compile(r"<command-args>(.*?)</command-args>", re.S)

TOOL_RESULT_MAX_CHARS = 2000
TOOL_RESULT_MAX_LINES = 30
TOOL_INPUT_MAX_CHARS = 600


# --------------------------------------------------------------------------- io

def cwd_project_dir(cwd: str | None = None) -> Path:
    """`/Users/me/proj` -> `~/.claude/projects/-Users-me-proj`."""
    return PROJECTS_ROOT / (cwd or os.getcwd()).replace("/", "-")


def resolve_session(arg: str | None) -> Path:
    if arg:
        p = Path(arg).expanduser()
        if p.is_file():
            return p
        hits = sorted(PROJECTS_ROOT.glob(f"*/{arg}.jsonl")) + \
            sorted(PROJECTS_ROOT.glob(f"*/*/subagents/{arg}.jsonl"))
        if hits:
            return hits[0]
        sys.exit(f"no transcript found for session {arg!r}")

    sid = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if sid:
        hits = sorted(PROJECTS_ROOT.glob(f"*/{sid}.jsonl"))
        if hits:
            return hits[0]

    root = cwd_project_dir()
    files = sorted(root.glob("*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not files:
        sys.exit(f"no *.jsonl transcripts under {root}")
    return files[0]


def read_entries(path: Path) -> list[dict]:
    out = []
    with path.open(errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


# ---------------------------------------------------------------------- helpers

def parse_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.astimezone()  # naive input = local time


def local_time(ts: str | None) -> str:
    if not ts:
        return ""
    dt = parse_ts(ts)
    return dt.astimezone().strftime("%Y-%m-%d %H:%M") if dt else ts


def slugify(text: str, fallback: str) -> str:
    s = re.sub(r"[^\w一-鿿]+", "-", (text or "").lower()).strip("-")
    return s[:60] or fallback


def clean_text(text: str) -> str:
    """Strip noise wrappers; render slash commands as `/name args`."""
    cmd = RX_CMD_NAME.search(text)
    if cmd:
        args = RX_CMD_ARGS.search(text)
        line = cmd.group(1).strip()
        if args and args.group(1).strip():
            line += " " + args.group(1).strip()
        text = RX_CMD_NAME.sub("", text)
        text = RX_CMD_ARGS.sub("", text)
        text = f"`{line}`\n\n" + text
    for rx in WRAPPERS:
        text = rx.sub("", text)
    return text.strip()


def truncate(text: str, max_chars: int, max_lines: int | None = None) -> str:
    total_chars, total_lines = len(text), len(text.splitlines())
    marker = ""
    if max_lines and total_lines > max_lines:
        text = "\n".join(text.splitlines()[:max_lines])
        marker = f"\n… [truncated, {total_lines} lines total]"
    if len(text) > max_chars:
        text = text[:max_chars]
        marker = marker or f"\n… [truncated, {max_chars} of {total_chars} chars shown]"
    return text + marker


def result_to_text(block: dict) -> str:
    content = block.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for b in content:
            if isinstance(b, dict) and b.get("type") == "text":
                parts.append(b.get("text", ""))
            elif isinstance(b, dict):
                parts.append(f"[{b.get('type')}]")
        return "\n".join(parts)
    return json.dumps(content, ensure_ascii=False) if content else ""


# ----------------------------------------------------------------------- render

RX_ASK_TAIL = re.compile(r"\s*Read the answers carefully.*$", re.S)


def tool_name_map(entries: list[dict]) -> dict[str, str]:
    """tool_use_id -> tool name, so tool_results can be attributed."""
    names: dict[str, str] = {}
    for e in entries:
        msg = e.get("message") or {}
        for b in msg.get("content") or []:
            if isinstance(b, dict) and b.get("type") in ("tool_use", "server_tool_use"):
                names[b.get("id")] = b.get("name")
    return names


def build_turns(entries: list[dict], full: bool, since: str | None,
                sidechains: bool = False) -> list[dict]:
    """Collapse the per-block jsonl lines into one turn per assistant response."""
    turns: list[dict] = []
    by_key: dict[str, dict] = {}
    names = tool_name_map(entries)
    since_dt = parse_ts(since)
    if since and not since_dt:
        sys.exit(f"--since {since!r} is not an ISO timestamp")

    for e in entries:
        if e.get("type") not in ("user", "assistant"):
            continue
        if e.get("isSidechain") and not sidechains:
            continue
        ts = e.get("timestamp", "")
        if since_dt:
            ets = parse_ts(ts)
            if ets and ets < since_dt:
                continue

        msg = e.get("message") or {}
        content = msg.get("content")
        blocks = [{"type": "text", "text": content}] if isinstance(content, str) else \
            (content if isinstance(content, list) else [])

        if e.get("type") == "user":
            # A compaction boundary carries the rolled-up summary of prior turns.
            if e.get("isCompactSummary"):
                body = "\n".join(b.get("text", "") for b in blocks if isinstance(b, dict))
                turns.append({"role": "compact", "ts": ts, "parts": [body.strip()]})
                continue
            if e.get("isMeta"):
                continue
            parts, human = [], False
            for b in blocks:
                if not isinstance(b, dict):
                    continue
                kind = b.get("type")
                if kind == "text":
                    t = clean_text(b.get("text", ""))
                    if t:
                        parts.append(t); human = True
                elif kind == "image":
                    parts.append("_[image]_"); human = True
                elif kind == "tool_result":
                    tool = names.get(b.get("tool_use_id"))
                    body = result_to_text(b).strip()
                    # The user's own words live in an AskUserQuestion result — keep
                    # them even in readable mode, where tool results are dropped.
                    if tool == "AskUserQuestion" and body:
                        parts.append("_(answered)_ " + RX_ASK_TAIL.sub("", body)); human = True
                    elif full and body:
                        label = f"↳ {tool} result" if tool else "↳ result"
                        parts.append(f"**{label}**\n```\n"
                                     + truncate(body, TOOL_RESULT_MAX_CHARS, TOOL_RESULT_MAX_LINES)
                                     + "\n```")
            if parts:
                turns.append({"role": "user" if human else "tool", "ts": ts, "parts": parts})
            continue

        # assistant — one jsonl line per content block, merged by message id
        key = msg.get("id") or e.get("requestId") or e.get("uuid")
        turn = by_key.get(key)
        if turn is None:
            turn = {"role": "assistant", "ts": ts, "parts": []}
            by_key[key] = turn
            turns.append(turn)
        for b in blocks:
            if not isinstance(b, dict):
                continue
            kind = b.get("type")
            if kind == "text":
                t = clean_text(b.get("text", ""))
                if t:
                    turn["parts"].append(t)
            elif kind == "thinking" and full:
                t = (b.get("thinking") or "").strip()
                if t:
                    turn["parts"].append("<details><summary>thinking</summary>\n\n"
                                         + t + "\n\n</details>")
            elif kind in ("tool_use", "server_tool_use") and full:
                args = json.dumps(b.get("input", {}), ensure_ascii=False)
                if len(args) > TOOL_INPUT_MAX_CHARS:
                    args = args[:TOOL_INPUT_MAX_CHARS] + " …"  # keep it a single inline span
                turn["parts"].append(f"**→ {b.get('name')}** `{args}`")
            elif kind == "advisor_tool_result" and full:
                turn["parts"].append("**↳ advisor**\n```\n"
                                     + truncate(result_to_text(b).strip(),
                                                TOOL_RESULT_MAX_CHARS, TOOL_RESULT_MAX_LINES)
                                     + "\n```")

    return [t for t in turns if any(p.strip() for p in t["parts"])]


HEADS = {
    "user": "## 👤 User",
    "assistant": "## 🤖 Assistant",
    "tool": "## 🔧 Tool result",
    "compact": "## ⤵ Context compacted",
}


def render(turns: list[dict], meta: dict) -> str:
    lines = [f"# {meta['title']}", ""]
    lines += [
        f"- Session: `{meta['session']}`",
        f"- Project: `{meta['cwd']}`",
        f"- Exported: {meta['exported']} ({meta['mode']} mode, {len(turns)} turns)",
        "",
        "---",
        "",
    ]
    for t in turns:
        head = HEADS[t["role"]]
        stamp = local_time(t["ts"])
        lines.append(f"{head}{'  ·  ' + stamp if stamp else ''}")
        lines.append("")
        lines.append("\n\n".join(p for p in t["parts"] if p.strip()))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


# ------------------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(description="Export a Claude Code conversation to markdown.")
    ap.add_argument("--session", help="session uuid or path to a .jsonl transcript")
    ap.add_argument("--full", action="store_true",
                    help="include thinking, tool calls and truncated tool results")
    ap.add_argument("-o", "--output", help="output path (default docs/reports/<date>-<slug>-transcript.md)")
    ap.add_argument("--since", help="only turns at/after this ISO timestamp (local time if no offset)")
    ap.add_argument("--include-sidechains", action="store_true",
                    help="include subagent turns (auto-on for a subagents/*.jsonl transcript)")
    ap.add_argument("--stdout", action="store_true", help="print to stdout instead of writing")
    args = ap.parse_args()

    path = resolve_session(args.session)
    entries = read_entries(path)
    sidechains = args.include_sidechains or path.parent.name == "subagents"
    turns = build_turns(entries, full=args.full, since=args.since, sidechains=sidechains)
    if not turns:
        sys.exit(f"no conversation turns found in {path}")

    title = next((e.get("customTitle") for e in reversed(entries) if e.get("type") == "custom-title"), None) \
        or next((e.get("aiTitle") for e in reversed(entries) if e.get("type") == "ai-title"), None) \
        or f"Session {path.stem[:8]}"
    cwd = next((e.get("cwd") for e in entries if e.get("cwd")), os.getcwd())
    first_ts = next((t["ts"] for t in turns if t["ts"]), None)
    date = (local_time(first_ts) or datetime.now().isoformat())[:10]

    body = render(turns, {
        "title": title,
        "session": path.stem,
        "cwd": cwd,
        "exported": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M"),
        "mode": "full" if args.full else "readable",
    })

    if args.stdout:
        sys.stdout.write(body)
        return

    # Relative to where the export is invoked (matching /report), not to the
    # session's own cwd — exporting another project's session collects it here.
    out = Path(args.output).expanduser() if args.output else \
        Path.cwd() / "docs" / "reports" / f"{date}-{slugify(title, path.stem[:8])}-transcript.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body)
    print(f"wrote {out}  ({len(turns)} turns, {len(body)} chars)")


if __name__ == "__main__":
    main()
