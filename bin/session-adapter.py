#!/usr/bin/env python3
"""Read, rename, or export the current Claude Code or Codex session.

The facade keeps one CLI for skills while delegating storage-specific work to
the host adapter: Codex app-server or the existing Claude transcript helpers.
It always requires an explicit session identity from an argument or environment
variable and never guesses the newest session.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CLAUDE_EXPORT = ROOT / "skills" / "report" / "export-transcript.py"
CLAUDE_LOG = ROOT / "bin" / "session-log.py"
CLAUDE_RENAME = ROOT / "skills" / "rename-session" / "rename.sh"


def detect_host(explicit: str | None) -> str:
    if explicit:
        return explicit
    if os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID"):
        return "codex"
    if os.environ.get("CLAUDE_CODE_SESSION_ID") or os.environ.get("CLAUDE_SESSION_ID"):
        return "claude"
    raise SystemExit(
        "Cannot detect session host. Pass --host codex|claude and --session, or run "
        "inside a host session with its session ID environment variable."
    )


def current_session_id(explicit: str | None, host: str) -> str:
    if explicit:
        return explicit
    if host == "codex":
        session_id = os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID")
        hint = "CODEX_THREAD_ID/CODEX_SESSION_ID"
    else:
        session_id = os.environ.get("CLAUDE_CODE_SESSION_ID") or os.environ.get("CLAUDE_SESSION_ID")
        hint = "CLAUDE_CODE_SESSION_ID/CLAUDE_SESSION_ID"
    if not session_id:
        raise SystemExit(
            f"No {host} session ID. Pass --session or set {hint}; refusing to guess the newest session."
        )
    return session_id


def claude_env(session_id: str) -> dict[str, str]:
    env = os.environ.copy()
    env["CLAUDE_CODE_SESSION_ID"] = session_id
    env["CLAUDE_SESSION_ID"] = session_id
    env.pop("CODEX_THREAD_ID", None)
    env.pop("CODEX_SESSION_ID", None)
    return env


def run_checked(command: list[str], *, env: dict[str, str] | None = None, capture: bool = False) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, env=env, text=True, capture_output=capture)
    if result.returncode:
        if capture:
            detail = (result.stderr or result.stdout).strip()
            raise SystemExit(detail or f"command failed ({result.returncode}): {' '.join(command)}")
        raise SystemExit(result.returncode)
    return result


def claude_title(session_id: str) -> tuple[str, str]:
    result = run_checked(
        [sys.executable, str(CLAUDE_EXPORT), "--show-title", "--session", session_id],
        env=claude_env(session_id),
        capture=True,
    )
    source, separator, title = result.stdout.strip().partition(": ")
    if not separator:
        raise SystemExit(f"unexpected Claude title response: {result.stdout.strip()!r}")
    return source, title


class AppServer:
    def __init__(self) -> None:
        codex = shutil.which("codex")
        if not codex:
            raise SystemExit("codex CLI is not installed or is not on PATH")
        try:
            self.proc = subprocess.Popen(
                [codex, "app-server", "--listen", "stdio://"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                bufsize=1,
            )
        except OSError as exc:
            raise SystemExit(f"failed to start Codex app-server: {exc}") from exc
        self.next_id = 1
        self.request(
            "initialize",
            {
                "clientInfo": {
                    "name": "dev-skills-session-adapter",
                    "title": "dev-skills session adapter",
                    "version": "1.0.0",
                },
                "capabilities": None,
            },
        )
        self.notify("initialized")

    def send(self, payload: dict[str, Any]) -> None:
        if not self.proc.stdin:
            raise SystemExit("Codex app-server stdin is unavailable")
        self.proc.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self.proc.stdin.flush()

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        payload: dict[str, Any] = {"method": method}
        if params is not None:
            payload["params"] = params
        self.send(payload)

    def request(self, method: str, params: dict[str, Any]) -> Any:
        request_id = self.next_id
        self.next_id += 1
        self.send({"method": method, "id": request_id, "params": params})
        if not self.proc.stdout:
            raise SystemExit("Codex app-server stdout is unavailable")
        while True:
            line = self.proc.stdout.readline()
            if not line:
                stderr = self.proc.stderr.read().strip() if self.proc.stderr else ""
                detail = f": {stderr}" if stderr else ""
                raise SystemExit(f"Codex app-server exited before replying to {method}{detail}")
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            if message.get("id") != request_id:
                continue
            if "error" in message:
                raise SystemExit(f"Codex app-server {method} failed: {message['error']}")
            return message.get("result")

    def close(self) -> None:
        if self.proc.poll() is not None:
            return
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
            self.proc.terminate()
            self.proc.wait(timeout=2)
        except (OSError, subprocess.TimeoutExpired):
            self.proc.kill()
            self.proc.wait()

    def __enter__(self) -> "AppServer":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def read_thread(server: AppServer, thread_id: str) -> dict[str, Any]:
    result = server.request("thread/read", {"threadId": thread_id, "includeTurns": False})
    return result["thread"]


def read_turns(server: AppServer, thread_id: str) -> list[dict[str, Any]]:
    turns: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        params: dict[str, Any] = {
            "threadId": thread_id,
            "limit": 100,
            "sortDirection": "asc",
            "itemsView": "full",
        }
        if cursor:
            params["cursor"] = cursor
        result = server.request("thread/turns/list", params)
        turns.extend(result.get("data") or [])
        cursor = result.get("nextCursor")
        if not cursor:
            return turns


def slugify(value: str, fallback: str) -> str:
    slug = re.sub(r"[^\w一-鿿]+", "-", value.lower()).strip("-")
    return slug[:60] or fallback


def timestamp(epoch: int | float | None, date_only: bool = False) -> str:
    if epoch is None:
        return ""
    value = datetime.fromtimestamp(epoch).astimezone()
    return value.strftime("%Y-%m-%d" if date_only else "%Y-%m-%d %H:%M")


def truncate(value: str, chars: int = 2000, lines: int = 30) -> str:
    original_lines = value.splitlines()
    marker = ""
    if len(original_lines) > lines:
        value = "\n".join(original_lines[:lines])
        marker = f"\n… [truncated, {len(original_lines)} lines total]"
    if len(value) > chars:
        value = value[:chars]
        marker = marker or f"\n… [truncated, {chars} chars shown]"
    return value + marker


def user_content(content: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for item in content:
        kind = item.get("type")
        if kind == "text":
            parts.append(item.get("text", ""))
        elif kind in ("image", "localImage"):
            parts.append("_[image]_")
        elif kind in ("audio", "localAudio"):
            parts.append("_[audio]_")
        elif kind == "skill":
            parts.append(f"_${item.get('name', 'skill')} invoked_")
        elif kind == "mention":
            parts.append(f"_mentioned {item.get('name', item.get('path', 'resource'))}_")
    return "\n\n".join(part for part in parts if part.strip())


def full_item(item: dict[str, Any]) -> str | None:
    kind = item.get("type", "unknown")
    if kind == "commandExecution":
        command = item.get("command", "")
        output = item.get("aggregatedOutput") or ""
        status = item.get("status", "unknown")
        body = f"**→ command ({status})**\n```shell\n{command}\n```"
        if output:
            body += f"\n\n**↳ output**\n```\n{truncate(output)}\n```"
        return body
    if kind == "fileChange":
        paths = [change.get("path") for change in item.get("changes") or [] if change.get("path")]
        return "**→ file changes** " + (", ".join(f"`{path}`" for path in paths) or "_(details unavailable)_")
    if kind == "mcpToolCall":
        return f"**→ MCP {item.get('server')}/{item.get('tool')}** `{truncate(json.dumps(item.get('arguments'), ensure_ascii=False), 600, 5)}`"
    if kind == "dynamicToolCall":
        return f"**→ tool {item.get('tool')}** `{truncate(json.dumps(item.get('arguments'), ensure_ascii=False), 600, 5)}`"
    if kind == "collabAgentToolCall":
        return f"**→ agent {item.get('tool')}** {item.get('status', '')}"
    if kind == "reasoning":
        summary = "\n".join(item.get("summary") or [])
        return f"<details><summary>reasoning summary</summary>\n\n{summary}\n\n</details>" if summary else None
    if kind == "webSearch":
        return f"**→ web search** `{item.get('query', '')}`"
    if kind == "contextCompaction":
        return "_Context compacted._"
    return None


def render_transcript(thread: dict[str, Any], turns: list[dict[str, Any]], full: bool) -> str:
    preview = (thread.get("preview") or "").splitlines()
    title = thread.get("name") or (preview[0][:80] if preview else "") or f"Session {thread['id'][:8]}"
    lines = [
        f"# {title}",
        "",
        f"- Session: `{thread['id']}`",
        f"- Project: `{thread.get('cwd', '')}`",
        f"- Exported: {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M')} ({'full' if full else 'readable'} mode, {len(turns)} turns)",
        "",
        "---",
        "",
    ]
    for turn in turns:
        stamp = timestamp(turn.get("startedAt"))
        for item in turn.get("items") or []:
            kind = item.get("type")
            heading: str | None = None
            body: str | None = None
            if kind == "userMessage":
                heading, body = "## 👤 User", user_content(item.get("content") or [])
            elif kind == "agentMessage":
                heading, body = "## 🤖 Assistant", item.get("text", "")
                questions = item.get("questions") or []
                if questions:
                    body += "\n\n" + "\n".join(f"- {q.get('title', '')}" for q in questions)
            elif kind == "plan":
                heading, body = "## 🤖 Assistant plan", item.get("text", "")
            elif full:
                heading, body = "## 🔧 Tool", full_item(item)
            elif kind == "contextCompaction":
                heading, body = "## ⤵ Context compacted", "_Context compacted._"
            if body and body.strip():
                lines.extend([f"{heading}{'  ·  ' + stamp if stamp else ''}", "", body.strip(), ""])
    return "\n".join(lines).rstrip() + "\n"


def command_show(args: argparse.Namespace) -> None:
    host = detect_host(args.host)
    session_id = current_session_id(args.session, host)
    if host == "codex":
        with AppServer() as server:
            metadata = read_thread(server, session_id)
        metadata["host"] = "codex"
        title = metadata.get("name") or "(untitled)"
        resolved_id = metadata["id"]
    else:
        source, title = claude_title(session_id)
        resolved_id = Path(session_id).stem if Path(session_id).is_file() else session_id
        metadata = {"host": "claude", "id": resolved_id, "name": title, "titleSource": source}
    if args.json:
        print(json.dumps(metadata, ensure_ascii=False, indent=2))
    else:
        print(f"{title} ({resolved_id}) [{host}]")


def command_rename(args: argparse.Namespace) -> None:
    host = detect_host(args.host)
    session_id = current_session_id(args.session, host)
    title = args.title.strip()
    if not title:
        raise SystemExit("title must not be empty")
    if host == "codex":
        with AppServer() as server:
            server.request("thread/name/set", {"threadId": session_id, "name": title})
            thread = read_thread(server, session_id)
        actual = thread.get("name")
    else:
        if Path(session_id).is_file():
            raise SystemExit("Claude rename requires a session ID, not a transcript path")
        run_checked(["bash", str(CLAUDE_RENAME), title], env=claude_env(session_id), capture=True)
        source, actual = claude_title(session_id)
        if source != "custom-title":
            raise SystemExit(f"rename verification failed: expected custom-title, got {source}")
    if actual != title:
        raise SystemExit(f"rename verification failed: expected {title!r}, got {actual!r}")
    print(f"Renamed {host} session {session_id} → {title}")


def command_export(args: argparse.Namespace) -> None:
    host = detect_host(args.host)
    session_id = current_session_id(args.session, host)
    if host == "codex":
        if args.since:
            raise SystemExit("--since is currently supported by the Claude adapter only")
        with AppServer() as server:
            thread = read_thread(server, session_id)
            turns = read_turns(server, session_id)
        body = render_transcript(thread, turns, args.full)
        if args.stdout:
            sys.stdout.write(body)
            return
        title = thread.get("name") or f"session-{session_id[:8]}"
        date = timestamp(thread.get("createdAt"), date_only=True) or datetime.now().astimezone().strftime("%Y-%m-%d")
        output = Path(args.output).expanduser().resolve() if args.output else Path.cwd() / "docs" / "reports" / f"{date}-{slugify(title, session_id[:8])}-transcript.md"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(body, encoding="utf-8")
        print(f"wrote {output}  ({len(turns)} turns, {len(body)} chars)")
        return

    env = claude_env(session_id)
    # Session logs are already filtered and redacted. Use them for readable
    # exports when the caller chose an output destination; fall back to the
    # older JSONL exporter when no log exists or richer rendering is needed.
    if not args.full and not args.since and not Path(session_id).is_file() and (args.output or args.stdout):
        log_command = [sys.executable, str(CLAUDE_LOG), "export", session_id]
        if args.output:
            log_command += ["-o", args.output]
        result = subprocess.run(log_command, env=env, text=True, capture_output=True)
        if result.returncode == 0:
            sys.stdout.write(result.stdout)
            return
        log_error = (result.stderr or result.stdout).strip()
        if "no session log for" not in log_error:
            raise SystemExit(log_error or f"Claude session-log export failed ({result.returncode})")
    command = [sys.executable, str(CLAUDE_EXPORT), "--session", session_id]
    if args.full:
        command.append("--full")
    if args.output:
        command += ["-o", args.output]
    if args.stdout:
        command.append("--stdout")
    if args.since:
        command += ["--since", args.since]
    run_checked(command, env=env)


def add_identity_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--host", choices=("codex", "claude"), help="override automatic host detection")
    parser.add_argument(
        "--session",
        "--thread",
        dest="session",
        help="session ID (or Claude transcript path); defaults to the detected host environment ID",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    show = subparsers.add_parser("show", help="show the current session title, ID, and host")
    add_identity_arguments(show)
    show.add_argument("--json", action="store_true", help="print full metadata as JSON")
    show.set_defaults(run=command_show)

    rename = subparsers.add_parser("rename", help="set and verify the session title")
    rename.add_argument("title")
    add_identity_arguments(rename)
    rename.set_defaults(run=command_rename)

    export = subparsers.add_parser("export", help="export conversation turns to Markdown")
    add_identity_arguments(export)
    export.add_argument("-o", "--output")
    export.add_argument("--stdout", action="store_true")
    export.add_argument("--full", action="store_true", help="include tool activity and truncated outputs")
    export.add_argument("--since", help="Claude only: include turns at or after an ISO timestamp")
    export.set_defaults(run=command_export)

    log = subparsers.add_parser("log", help="refresh/open a Codex working log (optionally watch)")
    add_identity_arguments(log)
    log.add_argument("-o", "--output", help="override the generated Markdown view path")
    log.add_argument("--open", action="store_true", help="open the refreshed log in the editor")
    log.add_argument("--stdout", action="store_true", help="print the refreshed log")
    log.add_argument("--note", help="append a local note, preserved across refreshes")
    log.add_argument("--watch", action="store_true", help="refresh until interrupted; no daemon installed")
    log.add_argument("--interval", type=float, default=15, help="watch interval in seconds (default 15)")
    from codex_history import command_log
    log.set_defaults(run=command_log)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.run(args)


if __name__ == "__main__":
    main()
