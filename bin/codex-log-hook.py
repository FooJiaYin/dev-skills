#!/usr/bin/env python3
"""Refresh a Codex working log from lifecycle hooks without blocking a turn."""
from __future__ import annotations

import fcntl
import json
import sys
import time

from codex_history import adapter, log_path, refresh_log


EVENTS = {"SessionStart", "UserPromptSubmit", "PostToolUse", "Stop"}


def handle(payload: dict, *, server_factory=None) -> dict:
    event = payload.get("hook_event_name")
    sid = payload.get("session_id")
    if event not in EVENTS or not isinstance(sid, str) or not sid:
        return {}
    try:
        if event == "PostToolUse" and isinstance(payload.get("cwd"), str):
            path = log_path({"id": sid, "cwd": payload["cwd"]})
            path.parent.mkdir(parents=True, exist_ok=True)
            # Background hooks can run together. Lock before checking freshness
            # so only one starts an app-server and rereads the thread.
            with path.with_suffix(".hook.lock").open("a") as gate:
                try:
                    fcntl.flock(gate, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    return {}
                if path.exists() and time.time() - path.stat().st_mtime < 5:
                    return {}
                server_factory = server_factory or adapter().AppServer
                with server_factory() as server:
                    path = refresh_log(server, sid)
        else:
            # Startup may precede persisted thread availability. The next
            # prompt/tool or Stop hook will refresh when the thread is ready.
            server_factory = server_factory or adapter().AppServer
            with server_factory() as server:
                path = refresh_log(server, sid)
    except (Exception, SystemExit) as exc:
        print(f"codex-log-hook: {event} refresh deferred: {exc}", file=sys.stderr)
        return {}
    if event == "SessionStart" and payload.get("source") in ("resume", "compact"):
        return {"hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": f"Codex session log refreshed: {path}. Read it if you need earlier decisions or file history."
        }}
    return {}


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        payload = {}
    # Stop requires JSON, not plain text. The same harmless output is accepted
    # by the other configured events.
    print(json.dumps(handle(payload), ensure_ascii=False))


if __name__ == "__main__":
    main()
