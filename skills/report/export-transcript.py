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

Default output is the readable dialogue only: user prompts (including ones sent
mid-turn) + assistant prose, one assistant block per user turn. Thinking blocks,
tool calls, tool results, IDE wrappers and system-reminders are dropped. `--full`
adds them back (file contents excepted: Read/Write/Edit show only the path).

Both modes list the files the session read or modified: a summary at the top and
one line per assistant turn, linked relative to the output file. Paths from the
Read/Write/Edit tools are exact; paths parsed out of Bash commands are a guess
and marked `~`.
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


# ------------------------------------------------------------------------ files
# Which files a turn read (R) or wrote (W). Dedicated tools are exact; paths
# pulled out of Bash commands are best-effort and flagged as inferred.

FILE_TOOLS_READ = {"Read"}
FILE_TOOLS_WRITE = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
FILE_TOOLS = FILE_TOOLS_READ | FILE_TOOLS_WRITE
IGNORED_PREFIXES = ("/dev/", "/tmp/", "/private/tmp/", "/private/var/", "/var/folders/")

# A path must end at a delimiter, so regex fragments like `/Users[^` inside a
# quoted grep pattern don't pass for a path.
_P = r"""[^\s'"`;|&<>()$*\[\]{}^\\]+(?=[\s'"`;|&)<>]|$)"""
_Q = r"""(?:'[^']*'|"[^"]*")"""
RX_CD = re.compile(r"""^\s*cd\s+['"]?([^\s'"&;|]+)['"]?\s*&&""")
RX_HEREDOC = re.compile(r"""<<-?\s*['"]?(\w+)['"]?""")
RX_PY_LAUNCH = re.compile(r"\b(?:python3?|node)\b")
SHELL_WRITE = [
    re.compile(r"(?<![-=<>\d])>>?\s*['\"]?(" + _P + ")"),
    re.compile(r"\btee\s+(?:-a\s+)?['\"]?(" + _P + ")"),
    re.compile(r"\bsed\s+-i(?:\s+'')?\s+(?:-e\s+)?" + _Q + r"\s+['\"]?(" + _P + ")"),
    re.compile(r"\b(?:mv|cp)\s+(?:-\w+\s+)*\S+\s+['\"]?(" + _P + ")"),
    re.compile(r"\brm\s+(?:-\w+\s+)*['\"]?(" + _P + ")"),
]
SHELL_READ = [
    re.compile(r"\b(?:cat|head|tail|wc|less)\s+(?:-\w+\s+(?:\d+\s+)?)*['\"]?(" + _P + ")"),
    re.compile(r"\bsed\s+-n\s+(?:" + _Q + r"|\S+)\s+['\"]?(" + _P + ")"),
    re.compile(r"\bgrep\b[^|;&\n]*?\s['\"]?([/~]" + _P + ")"),
]
PY_ASSIGN = re.compile(r"""(\w+)\s*=\s*(?:pathlib\.)?Path\(\s*['"]([^'"]+)['"]\s*\)""")
PY_PATH = re.compile(r"""(?:pathlib\.)?Path\(\s*['"]([^'"]+)['"]\s*\)(\.\w+)?""")
PY_OPEN = re.compile(r"""\bopen\(\s*['"]([^'"]+)['"]\s*(?:,\s*['"](\w+)['"])?""")


def iter_heredocs(cmd: str):
    """Yield (kind, text) for a shell command: kind is 'shell', 'code' (a
    heredoc fed to python/node) or 'content' (a heredoc written to a file)."""
    lines = cmd.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        yield "shell", line
        i += 1
        m = RX_HEREDOC.search(line)
        if not m:
            continue
        body = []
        while i < len(lines) and lines[i].strip() != m.group(1):
            body.append(lines[i])
            i += 1
        yield ("code" if RX_PY_LAUNCH.search(line) else "content"), "\n".join(body)
        if i < len(lines):
            yield "shell", lines[i]  # the closing delimiter
            i += 1


def collapse_heredocs(cmd: str) -> str:
    """Command text for display, with file-content heredoc bodies elided."""
    out = []
    for kind, text in iter_heredocs(cmd):
        out.append(f"… ({len(text.splitlines())} lines) …" if kind == "content" else text)
    return "\n".join(out)


def resolve_path(raw: str, cwd: str | None, allow_relative: bool) -> str | None:
    raw = raw.strip().rstrip(".,:")
    if re.search(r"[{}\[\]$]", raw):
        return None
    if raw.startswith("~"):
        path = os.path.expanduser(raw)
    elif raw.startswith("/"):
        path = raw
    elif allow_relative and cwd and re.search(r"\.\w{1,8}$", raw):
        # Relative paths are the fuzziest guess: keep them only if they resolve.
        path = os.path.join(cwd, raw)
        if not os.path.isfile(path):
            return None
    else:
        return None
    path = os.path.normpath(path)
    if "*" in path or path.startswith(IGNORED_PREFIXES) or os.path.isdir(path):
        return None
    return path


def bash_touches(cmd: str, cwd: str | None) -> list[tuple[str, str]]:
    m = RX_CD.match(cmd)
    here = os.path.join(cwd or "", os.path.expanduser(m.group(1))) if m else None
    base = here or cwd
    parts = list(iter_heredocs(cmd))
    shell = "\n".join(t for k, t in parts if k == "shell")
    out: list[tuple[str, str]] = []

    def add(raw: str, kind: str, allow_relative: bool) -> None:
        path = resolve_path(raw, base, allow_relative)
        if path:
            out.append((path, kind))

    # Relative paths in plain shell are only trusted after an explicit `cd`.
    for rx in SHELL_WRITE:
        for mm in rx.finditer(shell):
            add(mm.group(1), "W", bool(here))
    for rx in SHELL_READ:
        for mm in rx.finditer(shell):
            add(mm.group(1), "R", bool(here))
    for src in [shell] + [t for k, t in parts if k == "code"]:
        for var, raw in PY_ASSIGN.findall(src):
            written = re.search(rf"\b{re.escape(var)}\.write_(?:text|bytes)\b", src)
            add(raw, "W" if written else "R", True)
        for raw, attr in PY_PATH.findall(src):
            if attr in (".write_text", ".write_bytes"):
                add(raw, "W", True)
            elif attr in (".read_text", ".read_bytes", ".open"):
                add(raw, "R", True)
        for raw, mode in PY_OPEN.findall(src):
            add(raw, "W" if mode[:1] in ("w", "a", "x") else "R", True)
    return out


def tool_touches(block: dict, cwd: str | None) -> list[tuple[str, str, bool]]:
    """(path, 'R'|'W', exact) for one tool_use block."""
    name, inp = block.get("name"), block.get("input") or {}
    if name in FILE_TOOLS:
        path = inp.get("file_path") or inp.get("notebook_path")
        return [(path, "W" if name in FILE_TOOLS_WRITE else "R", True)] if path else []
    if name == "Bash":
        return [(p, k, False) for p, k in bash_touches(inp.get("command", ""), cwd)]
    return []


def add_touch(files: dict, path: str, kind: str, exact: bool) -> None:
    f = files.setdefault(path, {"kinds": set(), "exact": False})
    f["kinds"].add(kind)
    f["exact"] = f["exact"] or exact


RX_MD_LINK = re.compile(r"\]\(([^)\s]+)\)")


class Linker:
    """Builds links relative to the output file's directory."""

    def __init__(self, base_dir: Path, root: str):
        self.base, self.root = str(base_dir), root

    def href(self, path: str, anchor: str = "") -> str:
        rel = os.path.relpath(path, self.base) + (f"#{anchor}" if anchor else "")
        return f"<{rel}>" if re.search(r"[\s()<>]", rel) else rel

    def label(self, path: str) -> str:
        if path.startswith(self.root + os.sep):
            return os.path.relpath(path, self.root)
        home = str(Path.home())
        return "~" + path[len(home):] if path.startswith(home + os.sep) else path

    def link(self, path: str, text: str | None = None) -> str:
        return f"[{text or self.label(path)}]({self.href(path)})"

    def fix_prose(self, text: str) -> str:
        """Chat links are relative to the project root; re-point them at the
        output file's directory. Links that don't resolve are left alone."""
        def sub(m: re.Match) -> str:
            target = m.group(1)
            if re.match(r"[a-zA-Z][\w+.-]*:|#|/|<", target):
                return m.group(0)
            rel, _, anchor = target.partition("#")
            path = os.path.normpath(os.path.join(self.root, rel))
            if not rel or not os.path.exists(path):
                return m.group(0)
            return f"]({self.href(path, anchor)})"
        return RX_MD_LINK.sub(sub, text)


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


USER_BLOCKS = {"text", "image", "tool_result"}
ASSISTANT_BLOCKS = {"text", "thinking", "redacted_thinking", "tool_use", "server_tool_use"}


def blocks_of(content) -> list:
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    return content if isinstance(content, list) else []


def fenced(label: str, body: str) -> str:
    return (f"**{label}**\n```\n"
            + truncate(body, TOOL_RESULT_MAX_CHARS, TOOL_RESULT_MAX_LINES) + "\n```")


def unsupported(kind) -> str:
    # Surfaced rather than dropped, so new Claude Code block types don't vanish silently.
    return f"_[{kind} block not exported]_"


def human_texts(entries: list[dict]) -> set[str]:
    """Cleaned text of every real user entry, to de-dupe queued prompts."""
    seen = set()
    for e in entries:
        if e.get("type") != "user" or e.get("isMeta"):
            continue
        texts = [clean_text(b.get("text", "")) for b in blocks_of((e.get("message") or {}).get("content"))
                 if isinstance(b, dict) and b.get("type") == "text"]
        seen.update(t for t in texts if t)
        seen.add("\n\n".join(t for t in texts if t))
    return seen


def compact_note(e: dict) -> str:
    meta = e.get("compactMetadata") or {}
    pre, post = meta.get("preTokens"), meta.get("postTokens")
    size = f", {pre:,} → {post:,} tokens" if isinstance(pre, int) and isinstance(post, int) else ""
    return f"_Context compacted ({meta.get('trigger', 'unknown')}{size}). Turns above are still complete._"


def build_turns(entries: list[dict], full: bool, since: str | None,
                linker: Linker, sidechains: bool = False) -> list[dict]:
    """Collapse the per-block jsonl lines into one turn per assistant response."""
    turns: list[dict] = []
    by_key: dict[str, dict] = {}
    names = tool_name_map(entries)
    already_said = human_texts(entries)
    since_dt = parse_ts(since)
    if since and not since_dt:
        sys.exit(f"--since {since!r} is not an ISO timestamp")

    def new_turn(role: str, ts: str, parts: list[str]) -> dict:
        turn = {"role": role, "ts": ts, "parts": parts, "files": {}}
        turns.append(turn)
        return turn

    for e in entries:
        etype = e.get("type")
        if e.get("isSidechain") and not sidechains:
            continue
        ts = e.get("timestamp", "")
        if since_dt:
            ets = parse_ts(ts)
            if ets and ets < since_dt:
                continue

        if etype == "system":
            if e.get("subtype") == "compact_boundary":
                new_turn("compact", ts, [compact_note(e)])
            continue

        if etype == "attachment":
            att = e.get("attachment") or {}
            if att.get("type") != "queued_command":
                continue
            prompt = att.get("prompt")
            text = clean_text(prompt if isinstance(prompt, str) else "\n\n".join(
                b.get("text", "") for b in prompt or [] if isinstance(b, dict)))
            ts = ts or att.get("timestamp", "")
            if not text:
                continue
            is_human = att.get("commandMode") == "prompt" and (att.get("origin") or {}).get("kind") == "human"
            if is_human and text not in already_said:
                # A prompt sent while the agent was working is only recorded here.
                new_turn("user", ts, ["_(sent mid-turn)_ " + text])
            elif not is_human and full:
                new_turn("notice", ts, [fenced(f"↳ {att.get('commandMode') or 'notification'}", text)])
            continue

        if etype not in ("user", "assistant"):
            continue
        msg = e.get("message") or {}
        blocks = blocks_of(msg.get("content"))

        if etype == "user":
            if e.get("isCompactSummary"):
                body = "\n".join(b.get("text", "") for b in blocks if isinstance(b, dict)).strip()
                summary = f"<details><summary>summary of earlier turns</summary>\n\n{body}\n\n</details>"
                if turns and turns[-1]["role"] == "compact":
                    turns[-1]["parts"].append(summary)
                else:
                    new_turn("compact", ts, [summary])
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
                    elif full and body and tool not in FILE_TOOLS:  # no file contents
                        parts.append(fenced(f"↳ {tool} result" if tool else "↳ result", body))
                elif kind not in USER_BLOCKS:
                    parts.append(unsupported(kind))
            if parts:
                new_turn("user" if human else "tool", ts, parts)
            continue

        # assistant — one jsonl line per content block, merged by message id
        key = msg.get("id") or e.get("requestId") or e.get("uuid")
        turn = by_key.get(key)
        if turn is None:
            turn = by_key[key] = new_turn("assistant", ts, [])
        for b in blocks:
            if not isinstance(b, dict):
                continue
            kind = b.get("type")
            if kind in ("tool_use", "server_tool_use"):
                for path, rw, exact in tool_touches(b, e.get("cwd")):
                    add_touch(turn["files"], path, rw, exact)
            if kind == "text":
                t = linker.fix_prose(clean_text(b.get("text", "")))
                if t:
                    turn["parts"].append(t)
            elif not full and (kind in ASSISTANT_BLOCKS or str(kind).endswith("_tool_result")):
                continue
            elif kind == "thinking":
                t = (b.get("thinking") or "").strip()
                if t:
                    turn["parts"].append("<details><summary>thinking</summary>\n\n"
                                         + t + "\n\n</details>")
            elif kind == "redacted_thinking":
                turn["parts"].append("_[redacted thinking]_")
            elif kind in ("tool_use", "server_tool_use"):
                name, inp = b.get("name"), dict(b.get("input") or {})
                if name in FILE_TOOLS:
                    path = inp.get("file_path") or inp.get("notebook_path") or "?"
                    turn["parts"].append(f"**→ {name}** {linker.link(path)}")
                    continue
                if name == "Bash" and isinstance(inp.get("command"), str):
                    inp["command"] = collapse_heredocs(inp["command"])
                args = json.dumps(inp, ensure_ascii=False)
                if len(args) > TOOL_INPUT_MAX_CHARS:
                    args = args[:TOOL_INPUT_MAX_CHARS] + " …"  # keep it a single inline span
                turn["parts"].append(f"**→ {name}** `{args}`")
            elif str(kind).endswith("_tool_result"):
                label = "advisor" if kind == "advisor_tool_result" else kind
                turn["parts"].append(fenced(f"↳ {label}", result_to_text(b).strip()))
            else:
                turn["parts"].append(unsupported(kind))

    if not full:
        # One assistant block per user turn: fold consecutive assistant messages.
        merged: list[dict] = []
        for t in turns:
            prev = merged[-1] if merged else None
            if prev and prev["role"] == t["role"] == "assistant":
                prev["parts"] += t["parts"]
                for path, f in t["files"].items():
                    for rw in f["kinds"]:
                        add_touch(prev["files"], path, rw, f["exact"])
            else:
                merged.append(t)
        turns = merged

    return [t for t in turns if t["files"] or any(p.strip() for p in t["parts"])]


HEADS = {
    "user": "## 👤 User",
    "assistant": "## 🤖 Assistant",
    "tool": "## 🔧 Tool result",
    "notice": "## 🔔 Notification",
    "compact": "## ⤵ Context compacted",
}
INFERRED = " ~"


def split_files(files: dict) -> tuple[list[str], list[str]]:
    wrote = sorted(p for p, f in files.items() if "W" in f["kinds"])
    read = sorted(p for p, f in files.items() if "W" not in f["kinds"])
    return wrote, read


def render_file_summary(turns: list[dict], linker: Linker) -> list[str]:
    files: dict = {}
    for t in turns:
        for path, f in t["files"].items():
            for rw in f["kinds"]:
                add_touch(files, path, rw, f["exact"])
    if not files:
        return []
    wrote, read = split_files(files)
    lines = ["## 📁 Files", ""]
    for title, group in (("✏️ Modified", wrote), ("📄 Read", read)):
        if group:
            lines += [f"**{title}**", ""]
            lines += [f"- {linker.link(p)}{'' if files[p]['exact'] else INFERRED}" for p in group]
            lines.append("")
    lines += [f"_`{INFERRED.strip()}` = parsed from a Bash command (best effort); files reached "
              "only through variables or globs are not listed._", ""]
    return lines


def render_turn_files(files: dict, linker: Linker) -> str:
    def items(paths: list[str]) -> str:
        return ", ".join(linker.link(p, os.path.basename(p)) + ("" if files[p]["exact"] else INFERRED)
                         for p in paths)
    wrote, read = split_files(files)
    groups = ([f"✏️ {items(wrote)}"] if wrote else []) + ([f"📄 {items(read)}"] if read else [])
    return " · ".join(groups)


def render(turns: list[dict], meta: dict, linker: Linker) -> str:
    lines = [f"# {meta['title']}", ""]
    lines += [
        f"- Session: `{meta['session']}`",
        f"- Project: `{meta['cwd']}`",
        f"- Exported: {meta['exported']} ({meta['mode']} mode, {len(turns)} turns)",
        "",
    ]
    lines += render_file_summary(turns, linker)
    lines += ["---", ""]
    for t in turns:
        head = HEADS[t["role"]]
        stamp = local_time(t["ts"])
        lines.append(f"{head}{'  ·  ' + stamp if stamp else ''}")
        lines.append("")
        parts = [p for p in t["parts"] if p.strip()]
        if t["files"]:
            parts.append(render_turn_files(t["files"], linker))
        lines.append("\n\n".join(parts))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def resolve_title(entries: list[dict], path: Path) -> tuple[str, str]:
    """(source, title). `custom-title` means a human named this session."""
    for e in reversed(entries):
        if e.get("type") == "custom-title" and e.get("customTitle"):
            return "custom-title", e["customTitle"]
    for e in reversed(entries):
        if e.get("type") == "ai-title" and e.get("aiTitle"):
            return "ai-title", e["aiTitle"]
    return "none", f"Session {path.stem[:8]}"


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
    ap.add_argument("--show-title", action="store_true",
                    help="print '<source>: <title>' (source = custom-title | ai-title | none) and exit")
    args = ap.parse_args()

    path = resolve_session(args.session)
    entries = read_entries(path)
    if args.show_title:
        print("%s: %s" % resolve_title(entries, path))
        return
    sidechains = args.include_sidechains or path.parent.name == "subagents"
    _, title = resolve_title(entries, path)
    cwd = next((e.get("cwd") for e in entries if e.get("cwd")), os.getcwd())
    since_dt = parse_ts(args.since)
    first_ts = next((e["timestamp"] for e in entries
                     if e.get("type") in ("user", "assistant") and parse_ts(e.get("timestamp"))
                     and (not since_dt or parse_ts(e["timestamp"]) >= since_dt)), None)
    date = (local_time(first_ts) or datetime.now().isoformat())[:10]

    # Output path is decided first: file links are written relative to it.
    # Default is relative to where the export is invoked (matching /report), not
    # the session's own cwd — exporting another project's session collects it here.
    out = Path(args.output).expanduser().resolve() if args.output else \
        Path.cwd() / "docs" / "reports" / f"{date}-{slugify(title, path.stem[:8])}-transcript.md"
    linker = Linker(Path.cwd() if args.stdout else out.parent, cwd)

    turns = build_turns(entries, full=args.full, since=args.since, linker=linker, sidechains=sidechains)
    if not turns:
        sys.exit(f"no conversation turns found in {path}")

    body = render(turns, {
        "title": title,
        "session": path.stem,
        "cwd": cwd,
        "exported": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M"),
        "mode": "full" if args.full else "readable",
    }, linker)

    if args.stdout:
        sys.stdout.write(body)
        return

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body)
    print(f"wrote {out}  ({len(turns)} turns, {len(body)} chars)")


if __name__ == "__main__":
    main()
