"""Codex working logs and history search, using only the app-server API.

Logs are refreshable derived views, not native rollouts or write snapshots.
"""
from __future__ import annotations

import fcntl
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import date, datetime
from pathlib import Path


def load_helper(name, filename):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]


def adapter():
    return load_helper("dev_skills_session_adapter", "session-adapter.py")


def redact(text):
    return load_helper("dev_skills_claude_log", "session-log.py").redact(text)


def log_path(thread):
    root = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).expanduser()
    project = hashlib.sha256(thread.get("cwd", "").encode()).hexdigest()[:16]
    sid = thread["id"]
    if not re.fullmatch(r"[A-Za-z0-9_-]+", sid):
        raise ValueError("unsafe thread ID")
    return root / "dev-skills" / "session-logs" / project / f"{sid}.log.md"


def changed_paths(item, cwd):
    # A mentioned path or successful shell command is not proof of a write.
    if item.get("type") != "fileChange" or item.get("status") != "completed":
        return []
    paths = []
    for change in item.get("changes") or []:
        kind = change.get("kind") or {}
        for value in (change.get("path"), kind.get("move_path")):
            if value:
                p = Path(value).expanduser()
                paths.append(str((Path(cwd) / p).resolve()))
    return list(dict.fromkeys(paths))


def records(thread, turns):
    a = adapter()
    seen = set()
    for turn in turns:
        stamp = a.timestamp(turn.get("startedAt")) or "unknown-time"
        for index, item in enumerate(turn.get("items") or []):
            key = (turn["id"], item.get("id", index))
            if key in seen:
                continue
            seen.add(key)
            kind = item.get("type")
            tag, body = "tool", None
            if kind == "userMessage":
                tag, body = "user", a.user_content(item.get("content") or [])
            elif kind in ("agentMessage", "plan"):
                tag, body = "assistant", item.get("text", "")
                questions = item.get("questions") or []
                if questions:
                    body += "\n" + json.dumps(questions, ensure_ascii=False)
            elif kind == "fileChange":
                paths = changed_paths(item, thread.get("cwd", ""))
                if paths:
                    for path in paths:
                        yield stamp, "write", path + " tool=fileChange status=completed"
                    continue
                tag, body = "tool", f"fileChange status={item.get('status', 'unknown')} (not a confirmed write)"
            elif kind == "contextCompaction":
                tag, body = "compact", "Context compacted."
            elif kind == "reasoning":
                continue
            else:
                body = a.full_item(item)
                if kind == "webSearch":
                    tag = "web"
                if item.get("status") == "failed" or item.get("success") is False:
                    tag = "error"
                if body is None:
                    body = f"{kind} (details not rendered)"
            if body and body.strip():
                yield stamp, tag, body.strip()
        if turn.get("error"):
            yield stamp, "error", json.dumps(turn["error"], ensure_ascii=False)


def atomic_write(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".session-log-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(body)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def refresh_log(server, sid, output=None, note=None):
    a = adapter()
    thread = a.read_thread(server, sid)
    canonical = log_path(thread)
    target = Path(output).expanduser().resolve() if output else canonical
    target.parent.mkdir(parents=True, exist_ok=True)
    # Serialize refreshes of the same view; notes live outside the generated log.
    with target.with_suffix(".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        turns = a.read_turns(server, sid)
        notes_path = canonical.with_suffix(".notes.jsonl")
        if note is not None:
            notes_path.parent.mkdir(parents=True, exist_ok=True)
            with notes_path.open("a", encoding="utf-8") as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                f.write(json.dumps({"time": datetime.now().astimezone().isoformat(), "body": redact(note)}, ensure_ascii=False) + "\n")
        title = thread.get("name") or f"Session {sid[:8]}"
        lines = [f"# {title} · session {sid} · {thread.get('cwd', '')} · codex", "",
                 "Derived from persisted app-server turns. Refreshed on access; --watch polls while running.",
                 "Timestamps are turn start times. Tool output is abbreviated. [write] covers only completed fileChange events; shell/tool writes may be absent.", ""]
        for stamp, tag, body in records(thread, turns):
            lines.extend([f"[{stamp} {tag}] {body}", ""])
        if notes_path.exists():
            lines.extend(["## Local notes (preserved across refreshes)", ""])
            for line in notes_path.read_text().splitlines():
                n = json.loads(line)
                lines.extend([f"[{n['time']} note] {n['body']}", ""])
        body = redact("\n".join(lines).rstrip() + "\n")
        if not target.exists() or target.read_text() != body:
            atomic_write(target, body)
    return target


def open_in_editor(path):
    editor = shutil.which("code")
    command = [editor, str(path)] if editor else ["open" if sys.platform == "darwin" else "xdg-open", str(path)]
    result = subprocess.run(command)
    if result.returncode:
        raise SystemExit(f"Could not open log (exit {result.returncode}): {path}")


def command_log(args):
    a = adapter()
    host = a.detect_host(args.host)
    sid = a.current_session_id(args.session, host)
    if host != "codex":
        raise SystemExit("log is the Codex working-log command; use session-log.py for Claude hooks/logs")
    if args.interval < 1:
        raise SystemExit("--interval must be at least 1 second")
    if args.watch and args.stdout:
        raise SystemExit("--watch and --stdout cannot be combined")
    try:
        with a.AppServer() as server:
            first = True
            while True:
                path = refresh_log(server, sid, args.output, args.note if first else None)
                if first:
                    if args.stdout:
                        print(path.read_text(), end="")
                    else:
                        print(path, flush=True)
                    if args.open:
                        open_in_editor(path)
                first = False
                if not args.watch:
                    break
                time.sleep(args.interval)
    except KeyboardInterrupt:
        pass


def list_threads(server, cwd=None):
    seen = set()
    for archived in (False, True):
        cursor = None
        cursors = set()
        while True:
            params = {"limit": 100, "archived": archived, "sortKey": "created_at",
                      "sortDirection": "desc", "modelProviders": []}
            if cwd:
                params["cwd"] = str(Path(cwd).expanduser().resolve())
            if cursor:
                params["cursor"] = cursor
            result = server.request("thread/list", params)
            for thread in result.get("data") or []:
                if thread["id"] not in seen:
                    seen.add(thread["id"])
                    yield thread
            cursor = result.get("nextCursor")
            if not cursor:
                break
            if cursor in cursors:
                raise SystemExit("thread/list repeated a cursor; refusing an incomplete search")
            cursors.add(cursor)


def resolve_id(server, value):
    if value == "current":
        return adapter().current_session_id(None, "codex")
    if len(value) >= 36:
        return value
    matches = [t["id"] for t in list_threads(server) if t["id"].startswith(value)]
    if len(matches) != 1:
        raise SystemExit(f"Codex ID prefix {value!r}: {len(matches)} matches; provide a unique/full ID")
    return matches[0]


def search_text(item):
    kind = item.get("type")
    if kind == "userMessage":
        text = adapter().user_content(item.get("content") or [])
        for tag in ("environment_context", "skills_instructions", "system-reminder", "ide_opened_file", "skill"):
            text = re.sub(fr"<{tag}\b[^>]*>.*?</{tag}>", "", text, flags=re.S)
        return text
    if kind in ("agentMessage", "plan"):
        return item.get("text", "")
    if kind == "commandExecution":
        return item.get("command", "")
    if kind in ("mcpToolCall", "dynamicToolCall"):
        return json.dumps(item.get("arguments"), ensure_ascii=False)
    if kind == "webSearch":
        return item.get("query", "")
    return ""


def match_thread(thread, turns, topics, touched, since=None, until=None):
    stamps = [t.get("startedAt") for t in turns if t.get("startedAt") is not None]
    start = thread.get("createdAt")
    end = thread.get("updatedAt", start)
    if stamps:
        start = min(stamps + ([start] if start is not None else []))
        end = max(stamps + ([end] if end is not None else []))
    if since and end is not None and datetime.fromtimestamp(end).astimezone().date() < date.fromisoformat(since):
        return None
    if until and start is not None and datetime.fromtimestamp(start).astimezone().date() > date.fromisoformat(until):
        return None
    blobs = [thread.get("name") or ""]
    paths = []
    for turn in turns:
        for item in turn.get("items") or []:
            blobs.append(search_text(item))
            paths.extend(changed_paths(item, thread.get("cwd", "")))
    combined = "\n".join(blobs).casefold()
    if any(t.casefold() not in combined for t in topics if t):
        return None
    if touched:
        wanted = Path(touched).expanduser()
        def matches(p):
            if wanted.is_absolute():
                return Path(p) == wanted.resolve()
            return Path(p).parts[-len(wanted.parts):] == wanted.parts
        paths = [p for p in paths if matches(p)]
        if not paths:
            return None
    return {"thread": thread, "paths": sorted(set(paths)),
            "snippets": [b for b in blobs if any(t and t.casefold() in b.casefold() for t in topics)][:3]}


def search_main(args):
    a = adapter()
    if not args.open_id and not args.topic and not args.touched:
        raise SystemExit("provide --topic, --touched, or --open-id current|ID")
    for value in (args.since, args.until):
        if value:
            date.fromisoformat(value)
    if args.limit < 0 or (args.open is not None and args.open < 1):
        raise SystemExit("--limit must be nonnegative; --open must be at least 1")
    with a.AppServer() as server:
        if args.open_id:
            path = refresh_log(server, resolve_id(server, args.open_id))
            print(path)
            open_in_editor(path)
            return 0
        scopes = ["cwd", "all"] if args.escalate and args.scope == "cwd" else [args.scope]
        me = os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID")
        cache = {}
        hits = []
        failures = set()
        for scope in scopes:
            candidates = list(list_threads(server, (args.cwd or os.getcwd()) if scope == "cwd" else None))
            for topics in ([args.topic], (args.topic or "").split()):
                if not topics:
                    topics = [None]
                hits = []
                for thread in candidates:
                    sid = thread["id"]
                    if sid == me or sid in failures:
                        continue
                    if sid not in cache:
                        try:
                            cache[sid] = a.read_turns(server, sid)
                        except SystemExit as exc:
                            failures.add(sid)
                            print(f"# incomplete: could not read Codex {sid}: {exc}", file=sys.stderr)
                            continue
                    hit = match_thread(thread, cache[sid], topics, args.touched, args.since, args.until)
                    if hit:
                        hits.append(hit)
                if hits:
                    if topics != [args.topic]:
                        print("# no literal match in scope; matched all words")
                    break
            if hits:
                break
        hits.sort(key=lambda h: h["thread"].get("createdAt", 0), reverse=True)
        if args.limit:
            hits = hits[:args.limit]
        print(f"# host=codex scope={scope} matches={len(hits)} unreadable={len(failures)} (active + archived interactive threads)")
        for hit in hits:
            thread = hit["thread"]
            sid = thread["id"]
            title = " ".join((thread.get("name") or thread.get("preview") or "(untitled)").split())
            print(redact(f"{a.timestamp(thread.get('createdAt'))}  {sid}  [codex]  {title[:120]}"))
            if args.output == "graph":
                print(f"  forkedFromId={thread.get('forkedFromId') or '(not reported)'}")
            elif args.output == "full":
                print(f"  cwd: {thread.get('cwd', '')}\n  log: {log_path(thread)} (generated/refreshed when opened)")
                for value in hit["snippets"]:
                    print("  match: " + redact(a.truncate(value, 400, 5)))
                for value in hit["paths"]:
                    print("  fileChange: " + value)
        if args.touched:
            print("# Write evidence: completed fileChange only; shell/MCP writes are not attributed.")
        if args.open is not None:
            if args.open > len(hits):
                raise SystemExit(f"--open {args.open}: only {len(hits)} hits")
            path = refresh_log(server, hits[args.open - 1]["thread"]["id"])
            print(path)
            open_in_editor(path)
        if hits:
            print("# Resume: codex resume <ID>")
        return 2 if failures else (0 if hits else 1)


def legacy_cli(sub, argv):
    """Keep common session-log.py CLI operations useful inside Codex."""
    a = adapter()
    if sub == "export":
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("session", nargs="?")
        parser.add_argument("-o", "--output")
        parsed = parser.parse_args(argv)
        sid = a.current_session_id(parsed.session, "codex")
        with a.AppServer() as server:
            thread = a.read_thread(server, sid)
            turns = a.read_turns(server, sid)
        body = redact(a.render_transcript(thread, turns, False))
        notes_path = log_path(thread).with_suffix(".notes.jsonl")
        if notes_path.exists():
            notes = [json.loads(line) for line in notes_path.read_text().splitlines() if line.strip()]
            if notes:
                body += "\n## Local notes\n\n" + "\n\n".join(
                    f"### {n['time']}\n\n{redact(n['body'])}" for n in notes
                ) + "\n"
        if parsed.output:
            output = Path(parsed.output).expanduser().resolve()
            atomic_write(output, body)
            print(output)
        else:
            sys.stdout.write(body)
        return
    if sub == "writes" and any(v.startswith("--") for v in argv):
        raise SystemExit("Codex logs do not support --mine/--stage or Claude write snapshots")
    if sub == "backfill" and "--all" in argv:
        raise SystemExit("For Codex, backfill takes one explicit ID (or the current session); use find-session to select history")
    sid = a.current_session_id(argv[0] if argv and sub != "note" else None, "codex")
    with a.AppServer() as server:
        if sub == "writes":
            thread = a.read_thread(server, sid)
            paths = sorted({p for turn in a.read_turns(server, sid)
                            for item in turn.get("items") or []
                            for p in changed_paths(item, thread.get("cwd", ""))})
            print("# Completed fileChange evidence only; shell/tool writes and dirty/hunk attribution are unavailable.")
            print("\n".join(paths) if paths else "(no completed fileChange evidence)")
        else:
            path = refresh_log(server, sid, note=" ".join(argv) if sub == "note" else None)
            print(path.read_text(), end="") if sub == "show" else print(path)
