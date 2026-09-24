#!/usr/bin/env python3
"""Keep the Mac awake while this Claude session needs it (hook script).

  keep-awake.py agent   PreToolUse(Agent): caffeinate -i for 2h, restarted on each dispatch
  keep-awake.py remote  UserPromptSubmit: if Remote Control is connected, caffeinate -i until claude exits

Each session tracks only its own caffeinate via a pidfile — never touches anyone else's.
"""
import json, os, subprocess, sys


def comm(pid):
    r = subprocess.run(["ps", "-o", "ppid=,comm=", "-p", str(pid)], capture_output=True, text=True)
    parts = r.stdout.strip().split(None, 1)
    return (int(parts[0]), parts[1]) if len(parts) == 2 else (None, "")


def claude_pid():
    pid = os.getppid()
    for _ in range(10):
        ppid, name = comm(pid)
        if os.path.basename(name) == "claude":
            return pid
        if not ppid or ppid <= 1:
            return None
        pid = ppid
    return None


def own_caffeinate(pidfile):
    try:
        pid = int(open(pidfile).read().strip())
    except (OSError, ValueError):
        return None
    return pid if os.path.basename(comm(pid)[1]) == "caffeinate" else None


def spawn(args, pidfile):
    p = subprocess.Popen(["caffeinate", "-i", *args], stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    with open(pidfile, "w") as f:
        f.write(str(p.pid))


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        sid = json.load(sys.stdin).get("session_id") or "unknown"
    except Exception:
        sid = "unknown"
    pidfile = f"/tmp/claude-keepawake-{sid}-{mode}.pid"
    running = own_caffeinate(pidfile)

    if mode == "remote":
        if not os.environ.get("CLAUDE_CODE_BRIDGE_SESSION_ID") or running:
            return
        cpid = claude_pid()
        spawn(["-w", str(cpid)] if cpid else ["-t", "7200"], pidfile)
    elif mode == "agent":
        if running:
            os.kill(running, 15)
        spawn(["-t", "7200"], pidfile)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
