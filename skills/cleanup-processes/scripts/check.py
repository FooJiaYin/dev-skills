#!/usr/bin/env python3
"""Read-only resource check for macOS: what is eating memory and what looks unused.

Prints markdown (or JSON with --json). Never kills anything, never writes files.
Compatible with /usr/bin/python3 (3.9), stdlib only.
"""
from __future__ import annotations

import calendar
import glob
import json
import os
import re
import sys
import time

import subprocess

ENV = dict(os.environ, LC_ALL="C", PATH="/opt/homebrew/bin:/usr/local/bin:" + os.environ.get("PATH", "/usr/bin:/bin"))
NOW = time.time()
AUTOMATION_RE = re.compile(
    r"--headless|--remote-debugging-(port|pipe)|--enable-automation|playwright|puppeteer|"
    r"--user-data-dir=(/tmp|/private/tmp|/var/folders|/private/var/folders)"
)
DB_RE = re.compile(r"^(postgres|postmaster|mysqld|mariadbd|redis-server|mongod|clickhouse)", re.I)
SYSTEM_PREFIX = ("/System/", "/usr/libexec/", "/usr/sbin/", "/sbin/")
SYSTEM_NAMES = {"ControlCenter", "ControlCe", "rapportd", "launchd", "sharingd", "identityservicesd"}
IDLE_CLOSE_HOURS = 1.0
MCP_RE = re.compile(r"(playwright|chrome-devtools|browser|puppeteer)[^ ]*mcp|mcp[^ ]*(playwright|browser|chrome)", re.I)
BROWSER_RE = re.compile(r"^(Google Chrome|Google Chrome for Testing|Chromium|Safari|Firefox|Arc|Microsoft Edge|Brave Browser)$")
HOME = os.path.expanduser("~")
DEBUG_PORT_RE = re.compile(r"--remote-debugging-port=(\d+)")
# processes that forward a host port into a VM / container (the real service, often a DB, is inside)
FORWARDER_RE = re.compile(r"^(ssh|limactl|lima\S*|docker-proxy|com\.docker\.\S+|vpnkit\S*|gvproxy|qemu-system\S*|socat|kubectl)$")
DOCKER_DOWN_RE = re.compile(r"Cannot connect to the Docker daemon|failed to connect to the docker API|daemon is running", re.I)
UNSUPPORTED_NOTE = (
    "cleanup-processes check.py only supports macOS. Nothing was probed. Use this system's own tools to look at "
    "memory and swap, processes sorted by memory use, and processes listening on ports (with their parent "
    "process), then apply the signals and the three tiers in SKILL.md yourself."
)
FAILED = []  # (probe, one-line reason)
SESSION_INFO = {"dir": False, "files": 0, "valid": 0}
REQUIRED = ("ps", "top")


def note_fail(name, reason):
    if not any(n == name for n, _ in FAILED):
        FAILED.append((name, reason))


def required_failed():
    return [n for n, _ in FAILED if n in REQUIRED]


def is_gui(cmd):
    """Inside an app bundle (user-launched app; ppid 1 is normal there)."""
    return ".app/Contents/" in cmd.split(" -")[0]


def has_claude_history(cwd):
    """cwd (or a parent below $HOME) has a ~/.claude/projects/<encoded> dir."""
    path = cwd.rstrip("/")
    while path and path != HOME and path.startswith(HOME):
        if os.path.isdir(os.path.join(HOME, ".claude", "projects", re.sub(r"[^A-Za-z0-9]", "-", path))):
            return True
        path = os.path.dirname(path)
    return False


def run(cmd, timeout=15, name=None, empty_ok=()):
    """stdout, or None on failure (recorded under `name` when given).
    Exit codes in `empty_ok` with no stdout/stderr mean "no matches" (lsof exits 1 then) and return ""."""
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=ENV)
    except FileNotFoundError:
        reason = "找不到指令 %s" % cmd[0]
    except subprocess.TimeoutExpired:
        reason = "逾時（%d 秒）" % timeout
    except Exception as e:
        reason = "%s: %s" % (type(e).__name__, e)
    else:
        if out.returncode == 0 or out.stdout:
            return out.stdout
        if out.returncode in empty_ok and not out.stderr.strip():
            return ""
        err = (out.stderr.strip().splitlines() or [""])[0][:160]
        if name == "docker" and DOCKER_DOWN_RE.search(out.stderr):
            CONTAINER_NOTES.append("docker：daemon 沒在跑（沒有容器）")
            return None
        reason = "exit %d：%s" % (out.returncode, err)
    if name:
        note_fail(name, reason)
    return None


CONTAINER_NOTES = []


def parse_size(s):
    """top sizes like 1315M, 12G+, 512K-, 0B -> MB."""
    m = re.match(r"^([\d.]+)([BKMGT]?)", s.strip())
    if not m:
        return 0.0
    v = float(m.group(1))
    mult = {"B": 1.0 / 1048576, "K": 1.0 / 1024, "M": 1.0, "G": 1024.0, "T": 1048576.0, "": 1.0 / 1048576}
    return v * mult[m.group(2)]


def fmt_mb(mb):
    return "%.1f GB" % (mb / 1024) if mb >= 1024 else "%d MB" % mb


def fmt_age(sec):
    if sec is None:
        return "?"
    h = sec / 3600.0
    return "%.1f h" % h if h < 48 else "%.1f d" % (h / 24)


def fmt_time(ts):
    return time.strftime("%m-%d %H:%M", time.localtime(ts)) if ts else "?"


# ---------------------------------------------------------------- processes
def load_ps():
    procs = {}
    out = run(["ps", "-axo", "pid=,ppid=,lstart=,command="], name="ps")
    for line in (out or "").splitlines():
        parts = line.split()
        if len(parts) < 7:
            continue
        try:
            pid, ppid = int(parts[0]), int(parts[1])
            start = time.mktime(time.strptime(" ".join(parts[2:7]), "%a %b %d %H:%M:%S %Y"))
        except ValueError:
            continue
        # command = rest of the line after the 7th token (keep inner spaces)
        m = re.match(r"\s*\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+\s?(.*)$", line)
        procs[pid] = {"pid": pid, "ppid": ppid, "start": start, "cmd": m.group(1).strip() if m else ""}
    if out is not None and not procs:
        note_fail("ps", "輸出裡解析不出任何程序")
    return procs


def category_of(cmd):
    apps = re.findall(r"([^/]+)\.app/", cmd.split(" -")[0])
    if apps:
        inner = apps[-1]
        if re.match(r"^(python|ruby|node|java)", inner, re.I):
            return inner.lower().rstrip("0123456789.")  # Python.app inside Xcode -> python
        return apps[0]  # helpers roll up to the top-level app (Chrome / VS Code helpers)
    m = re.search(r"([^/]+)\.xpc/", cmd)
    if m:
        return m.group(1)
    first = cmd.split()[0] if cmd.split() else "?"
    base = os.path.basename(first)
    if re.match(r"^python\d*(\.\d+)*$", base, re.I):
        return "python"
    return base or "?"


def ancestors(pid, procs):
    chain, seen = [], set()
    cur = procs.get(pid)
    while cur and cur["ppid"] not in seen and cur["ppid"] > 0:
        seen.add(cur["pid"])
        parent = procs.get(cur["ppid"])
        if not parent:
            break
        chain.append(parent["pid"])
        cur = parent
    return chain


def load_top():
    mem = {}
    out = run(["top", "-l", "1", "-o", "mem", "-n", "400", "-stats", "pid,command,mem,cmprs"], timeout=30, name="top")
    started = False
    for line in (out or "").splitlines():
        if line.startswith("PID"):
            started = True
            continue
        if not started:
            continue
        parts = line.split()
        if len(parts) < 3:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        mem[pid] = (parse_size(parts[-2]), parse_size(parts[-1]))
    if out is not None and not mem:
        note_fail("top", "輸出裡解析不出任何程序")
    return mem


# ---------------------------------------------------------------- sessions
def parse_proc_start(s):
    """procStart in the session json is ctime-style UTC ("Wed Nov 18 18:38:12 2026")."""
    try:
        return float(calendar.timegm(time.strptime(" ".join(str(s).split()), "%a %b %d %H:%M:%S %Y")))
    except (TypeError, ValueError):
        return None


def load_sessions(procs):
    sessions = {}
    sdir = os.path.join(HOME, ".claude", "sessions")
    SESSION_INFO["dir"] = os.path.isdir(sdir)
    files = glob.glob(os.path.join(sdir, "*.json"))
    SESSION_INFO["files"] = len(files)
    bad = 0
    for path in files:
        try:
            with open(path) as f:
                d = json.load(f)
            pid = int(d.get("pid"))
        except Exception:
            bad += 1
            continue
        SESSION_INFO["valid"] += 1
        try:
            os.kill(pid, 0)  # signal 0 = existence probe (macOS only; main() exits first elsewhere)
        except Exception:
            continue
        p = procs.get(pid)
        started = d.get("startedAt")
        unverified = not procs  # ps failed: the pid is alive but may have been reused
        if not unverified:
            ref, tol = parse_proc_start(d.get("procStart")), 5
            if ref is None and started:
                ref, tol = started / 1000.0, 120
            if p is None or ref is None or abs(p["start"] - ref) > tol:
                continue  # pid reused by an unrelated process, or nothing to check it against
        su = d.get("statusUpdatedAt")
        sessions[pid] = {
            "pid": pid,
            "sessionId": d.get("sessionId", ""),
            "name": d.get("name") or "?",
            "status": d.get("status") or "?",
            "hours_in_status": (NOW - su / 1000.0) / 3600.0 if su else None,
            "entrypoint": d.get("entrypoint", "?"),
            "project": os.path.basename(d.get("cwd", "") or "?"),
            "cwd": d.get("cwd", ""),
            "started": (started / 1000.0) if started else (p["start"] if p else None),
            "self": False,
            "unverified": unverified,
        }
    if bad:
        note_fail("讀 session 檔", "%d 個 %s/*.json 讀不了或格式不對" % (bad, sdir))
    me = os.getpid()
    for pid in [me] + ancestors(me, procs):
        if pid in sessions:
            sessions[pid]["self"] = True  # this session and any session above it
    return sessions


def owner_session(pid, procs, sessions):
    for a in [pid] + ancestors(pid, procs):
        if a in sessions:
            return sessions[a]
    return None


# ---------------------------------------------------------------- analysis
def classify(procs, sessions):
    for pid, p in procs.items():
        p["cat"] = p["base"] = "claude" if pid in sessions else category_of(p["cmd"])
    for pid, p in procs.items():
        chain = ancestors(pid, procs)
        root = p
        for a in chain:
            if procs[a]["base"] == p["base"]:
                root = procs[a]
            else:
                break
        p["root"] = root["pid"]
        p["mcp"] = bool(MCP_RE.search(p["cmd"]))
        p["automated"] = not p["mcp"] and pid not in sessions and bool(AUTOMATION_RE.search(root["cmd"]) or AUTOMATION_RE.search(p["cmd"]))
        p["gui"] = is_gui(root["cmd"]) and p["base"] not in ("python", "ruby", "node", "java")
        system = root["cmd"].startswith(SYSTEM_PREFIX)
        p["orphan"] = root["ppid"] == 1 and not system and (p["automated"] or not p["gui"])
        if p["automated"]:
            p["cat"] = p["cat"] + " (automation/headless)"


def top_groups(procs, mem, limit=12):
    groups = {}
    for pid, p in procs.items():
        g = groups.setdefault(p["cat"], {"cat": p["cat"], "count": 0, "mem": 0.0, "cmprs": 0.0,
                                         "earliest": None, "orphan": 0, "automated": 0})
        g["count"] += 1
        m, c = mem.get(pid, (0.0, 0.0))
        g["mem"] += m
        g["cmprs"] += c
        g["earliest"] = p["start"] if g["earliest"] is None else min(g["earliest"], p["start"])
        g["orphan"] += 1 if p["orphan"] else 0
        g["automated"] += 1 if p["automated"] else 0
    return sorted(groups.values(), key=lambda g: -(g["mem"] + g["cmprs"]))[:limit]


def listeners(procs, sessions):
    out = run(["lsof", "-iTCP", "-sTCP:LISTEN", "-P", "-n"], timeout=20, name="lsof", empty_ok=(1,))
    seen, rows = set(), []
    for line in (out or "").splitlines()[1:]:
        parts = line.split()
        if len(parts) < 9:
            continue
        try:
            pid = int(parts[1])
        except ValueError:
            continue
        port = parts[8].rsplit(":", 1)[-1]
        if (pid, port) in seen:
            continue
        seen.add((pid, port))
        p = procs.get(pid, {"cmd": parts[0], "ppid": 0, "start": None, "cat": parts[0], "orphan": False})
        exe = p["cmd"].split(" -")[0]
        if parts[0] in SYSTEM_NAMES or exe.startswith(SYSTEM_PREFIX):
            continue
        cwd = ""
        c = run(["lsof", "-a", "-p", str(pid), "-d", "cwd", "-Fn"], timeout=10)
        for l in (c or "").splitlines():
            if l.startswith("n"):
                cwd = l[1:]
        sess = owner_session(pid, procs, sessions)
        rows.append({
            "port": port, "pid": pid, "cmd": p["cmd"][:80], "cat": p.get("cat", parts[0]),
            "start": p["start"], "age": (NOW - p["start"]) if p["start"] else None, "cwd": cwd,
            "parent_alive": p["ppid"] in procs and p["ppid"] != 1,
            "exe": os.path.basename(exe.split()[0]) if exe.split() else parts[0],
            "lsof_cmd": parts[0],
            "session_pid": sess["pid"] if sess else None,
            "session": sess["name"] if sess else None,
            "session_status": sess["status"] if sess else None,
            "session_self": bool(sess and sess["self"]),
            "orphan": p.get("orphan", False),
        })
    rows.sort(key=lambda r: int(r["port"]) if r["port"].isdigit() else 0)
    return rows


def containers():
    res = {"colima": None, "docker": None}
    out = run(["colima", "list"], timeout=15, name="colima")
    if out:
        res["colima"] = out.strip()
    out = run(["docker", "stats", "--no-stream", "--format", "{{.Name}} {{.MemUsage}}"], timeout=20, name="docker")
    if out is not None:
        rows, total = [], 0.0
        unit_mb = {"B": 1.0 / 1048576, "K": 1.0 / 1024, "M": 1.0, "G": 1024.0, "T": 1048576.0}
        for line in out.splitlines():
            m = re.match(r"^(\S+)\s+([\d.]+)\s*([kKMGT]?)i?B", line)
            if not m:
                continue
            v = float(m.group(2))
            mb = v * unit_mb[(m.group(3) or "B").upper()]
            total += mb
            rows.append((m.group(1), mb))
        res["docker"] = {"rows": rows, "total_mb": total}
    return res


def child_ports_text(s, ports):
    """Listening ports of processes under session s (they die with it)."""
    if any(n == "lsof" for n, _ in FAILED):
        return "無法確認（lsof 失敗）"
    rows = [r for r in ports if r["session_pid"] == s["pid"] and r["pid"] != s["pid"]]
    return "、".join(":%s %s（pid %d）" % (r["port"], r["cmd"][:50], r["pid"]) for r in rows) or "無"


def debug_clients(root, procs, ports):
    """Live processes outside the browser's own tree connected to its debugging port.
    Returns None when it can't be told (no --remote-debugging-port, port unknown, lsof failed)."""
    tree = {pid for pid in procs if pid == root or root in ancestors(pid, procs)}
    if not any(DEBUG_PORT_RE.search(procs[pid]["cmd"]) for pid in tree):
        return None  # pipe-only (playwright) or no debugging flag at all
    dports = {m.group(1) for pid in tree for m in [DEBUG_PORT_RE.search(procs[pid]["cmd"])] if m and m.group(1) != "0"}
    if not any(n == "lsof" for n, _ in FAILED):
        dports |= {r["port"] for r in ports if r["pid"] in tree}  # covers --remote-debugging-port=0
    if not dports:
        return None
    clients = []
    for port in sorted(dports):
        out = run(["lsof", "-nP", "-iTCP:%s" % port, "-sTCP:ESTABLISHED"], timeout=10, empty_ok=(1,))
        if out is None:
            return None
        for line in out.splitlines()[1:]:
            parts = line.split()
            if len(parts) < 9 or "->" not in parts[8]:
                continue
            try:
                pid = int(parts[1])
            except ValueError:
                continue
            if parts[8].split("->", 1)[1].endswith(":" + port) and pid not in tree:
                clients.append("pid %d %s → :%s" % (pid, procs.get(pid, {}).get("cat", parts[0]), port))
    return sorted(set(clients))


def candidates(procs, sessions, ports, ctr):
    close, ask, keep = [], [], []
    for s in sessions.values():
        label = "session %s (pid %d, %s)" % (s["name"], s["pid"], s["sessionId"][:8])
        h = s["hours_in_status"]
        if s["self"]:
            keep.append((label, "自己這個 session"))
        elif s["status"] in ("busy", "shell"):
            keep.append((label, "狀態 %s" % s["status"]))
        elif s["status"] == "idle" and h is not None and h >= IDLE_CLOSE_HOURS:
            close.append((label, "idle %s；底下在聽 port、會一起關：%s；接回 claude --resume %s"
                          % (fmt_age(h * 3600), child_ports_text(s, ports), s["sessionId"])))
        else:
            ask.append((label, "狀態 %s，已 %s" % (s["status"], fmt_age(h * 3600 if h is not None else None))))
    # automated browsers / orphan roots (one row per root)
    roots = {}
    for p in procs.values():
        if p["automated"]:
            roots.setdefault(p["root"], 0)
            roots[p["root"]] += 1
    for root, n in roots.items():
        r = procs[root]
        sess = owner_session(root, procs, sessions)
        label = "%s root pid %d（%d 個程序）" % (r["cat"], root, n)
        if r["orphan"]:
            clients = debug_clients(root, procs, ports)
            age = fmt_age(NOW - r["start"])
            if clients is None:
                ask.append((label, "孤兒＋自動化參數，開了 %s；查不出有沒有人連著除錯 port（沒有 port 或 lsof 失敗）" % age))
            elif clients:
                ask.append((label, "孤兒＋自動化參數，開了 %s；但有活著的程序連著除錯 port：%s" % (age, "、".join(clients))))
            else:
                close.append((label, "孤兒＋自動化參數，開了 %s；沒有任何程序連著它的除錯 port" % age))
        elif sess and (sess["self"] or sess["status"] in ("busy", "shell")):
            keep.append((label, "屬於 session %s（%s）" % (sess["name"], sess["status"])))
        else:
            ask.append((label, "自動化參數，開它的程序還在（session：%s）" % (sess["name"] if sess else "無")))
    # MCP daemons that are not browsers themselves (e.g. playwright-mcp node)
    mcp = [p for p in procs.values() if p["mcp"]]
    if mcp:
        owners = {}
        for p in mcp:
            s = owner_session(p["pid"], procs, sessions)
            key = s["name"] if s else ("孤兒" if p["orphan"] else "非 Claude（%s）" % procs[p["ppid"]]["cat"] if p["ppid"] in procs else "?")
            owners.setdefault(key, []).append(str(p["pid"]))
        detail = "；".join("%s: %s" % (k, ",".join(v)) for k, v in sorted(owners.items()))
        ask.append(("瀏覽器自動化 MCP 背景程式 ×%d" % len(mcp), "多半跟著 session 開、session 關了一起走。pid 依歸屬 → " + detail))
    live_cwds = [(s["cwd"], s) for s in sessions.values() if s["cwd"]]
    for r in ports:
        label = ":%s %s pid %d" % (r["port"], r["cat"], r["pid"])
        if r["pid"] in sessions:
            continue  # the session's own port; handled by the session row
        if procs.get(r["pid"], {}).get("automated"):
            continue  # an automated browser's port; handled by its root row above
        if DB_RE.match(r["cat"]):
            keep.append((label, "資料庫"))
        elif FORWARDER_RE.match(r["exe"]) or FORWARDER_RE.match(r["lsof_cmd"]):
            keep.append((label, "port forwarder，可能是容器裡的資料庫；要關就關 VM／容器本身，不要關它"))
        elif r["session_self"]:
            keep.append((label, "本 session 開的（收尾時自己關）"))
        elif r["session"]:
            if r["session_status"] in ("busy", "shell"):
                keep.append((label, "屬於 session %s（%s）" % (r["session"], r["session_status"])))
            else:
                ask.append((label, "屬於 session %s（%s）" % (r["session"], r["session_status"])))
        elif r["orphan"]:
            # always ask: nothing here proves who started it (nohup by the user, a demo left up on purpose,
            # a resumed session with a newer startedAt, a Codex session, ...). Just list the signals.
            near = [s for c, s in live_cwds if r["cwd"] and (r["cwd"] + "/").startswith(c.rstrip("/") + "/")]
            known = [s for s in near if r["start"] is not None and s["started"] is not None]
            older_than = [s["name"] for s in known if r["start"] < s["started"]]
            newer_than = [s["name"] for s in known if r["start"] >= s["started"]]
            sig = ["孤兒 server，開了 %s" % fmt_age(r["age"]),
                   "cwd %s（%s Claude 紀錄）" % (r["cwd"] or "?", "有" if r["cwd"] and has_claude_history(r["cwd"]) else "沒有")]
            if not near:
                sig.append("該路徑沒有活著的 session")
            if older_than:
                sig.append("比活著的 session %s 早開" % "、".join(older_than))
            if newer_than:
                sig.append("晚於 %s 開（可能是它開的）" % "、".join(newer_than))
            ask.append((label, "；".join(sig)))
        elif procs.get(r["pid"], {}).get("gui") and not r["orphan"]:
            keep.append((label, "使用者開的應用程式本身的 port"))
        else:
            ask.append((label, "歸屬拿不準（父程序還在，但不是 Claude session）"))
    if ctr.get("colima") and "Running" in ctr["colima"]:
        ask.append(("colima VM", "關了跑測試要重開；容器實際合計 %s" % fmt_mb((ctr.get("docker") or {}).get("total_mb", 0))))
    users = sorted({p["cat"] for p in procs.values() if not p["automated"] and BROWSER_RE.match(p["cat"])})
    for u in users:
        keep.append((u, "使用者自己的瀏覽器（無自動化參數）"))
    if any(os.path.basename(p["cmd"].split()[0] if p["cmd"] else "") == "caffeinate" for p in procs.values()):
        keep.append(("caffeinate", "防睡；絕不 pkill／killall"))
    return close, ask, keep


# ---------------------------------------------------------------- output
def table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for r in rows:
        lines.append("| " + " | ".join(str(c).replace("|", "/") for c in r) + " |")
    return "\n".join(lines) if rows else "(無)"


def main():
    if sys.platform != "darwin":
        # nothing is probed off macOS; on Windows os.kill(pid, 0) would send Ctrl+C
        if "--json" in sys.argv:
            print(json.dumps({"supported": False, "platform": sys.platform, "note": UNSUPPORTED_NOTE}, ensure_ascii=False))
        else:
            print("# cleanup-processes check: unsupported platform (%s)\n\n%s" % (sys.platform, UNSUPPORTED_NOTE))
        return

    procs = load_ps()
    mem = load_top()
    sessions = load_sessions(procs)
    classify(procs, sessions)
    groups = top_groups(procs, mem)
    ports = listeners(procs, sessions)
    ctr = containers()
    insufficient = required_failed()
    close, ask, keep = ([], [], []) if insufficient else candidates(procs, sessions, ports, ctr)

    swap = run(["sysctl", "-n", "vm.swapusage"], name="sysctl vm.swapusage") or ""
    memsize = (run(["sysctl", "-n", "hw.memsize"], name="sysctl hw.memsize") or "").strip()
    load = (run(["uptime"], name="uptime") or "").strip()
    sw = dict(re.findall(r"(total|used|free) = ([\d.]+)M", swap))
    swap_pct = (float(sw["used"]) / float(sw["total"]) * 100) if sw.get("total") and float(sw["total"]) else 0.0
    no_sessions = not SESSION_INFO["dir"] or SESSION_INFO["valid"] == 0
    session_note = "找不到 Claude Code 的 session 資料（Codex 或其他 host 的 session 不會列在這裡）"

    if "--json" in sys.argv:
        print(json.dumps({"supported": True, "failed_probes": FAILED,
                          "swap": sw, "swap_pct": swap_pct, "memsize": int(memsize) if memsize.isdigit() else None,
                          "uptime": load, "groups": groups, "sessions": list(sessions.values()),
                          "sessions_note": session_note if no_sessions else None, "ports": ports,
                          "containers": ctr, "container_notes": CONTAINER_NOTES,
                          "candidates": None if insufficient else {"close": close, "ask": ask, "keep": keep}},
                         ensure_ascii=False, indent=1, default=str))
        return

    out = ["# cleanup-processes check（%s，唯讀）" % time.strftime("%Y-%m-%d %H:%M")]
    if FAILED:
        out.append("\n> ⚠ 這些探測失敗，下面的空表不代表沒有東西：")
        for n, why in FAILED:
            out.append("> - %s：%s" % (n, why))
    out.append("\n## 1. 總覽")
    out.append("- RAM：%s" % (fmt_mb(int(memsize) / 1048576.0) if memsize.isdigit() else "?（sysctl 失敗）"))
    if sw:
        out.append("- swap：used %s / total %s（%.0f%%）" % (fmt_mb(float(sw.get("used", 0))), fmt_mb(float(sw.get("total", 0))), swap_pct))
    out.append("- load：%s" % (load.split("load averages:")[-1].strip() if "load averages" in load else load))

    out.append("\n## 2. 實際佔用前幾名（同類合併；MEM／CMPRS 取自 top）")
    out.append(table(["類別", "個數", "MEM", "CMPRS", "最早啟動", "訊號"],
                     [(g["cat"], g["count"], fmt_mb(g["mem"]), fmt_mb(g["cmprs"]), fmt_time(g["earliest"]),
                       "孤兒 %d／自動化 %d" % (g["orphan"], g["automated"]) if g["orphan"] or g["automated"] else "")
                      for g in groups]))

    out.append("\n## 3. Claude sessions")
    order = {"idle": 0, "waiting": 1, "shell": 2, "busy": 3}
    srows = sorted(sessions.values(), key=lambda s: (order.get(s["status"], 9), -(s["hours_in_status"] or 0)))
    if no_sessions:
        out.append(session_note)
    else:
        out.append(table(["名稱", "狀態", "在此狀態", "入口", "專案", "pid", "sessionId", ""],
                         [(s["name"], s["status"], fmt_age(s["hours_in_status"] * 3600 if s["hours_in_status"] is not None else None),
                           s["entrypoint"], s["project"], s["pid"], s["sessionId"][:8],
                           "← 自己" if s["self"] else ("pid 未驗證（ps 失敗）" if s["unverified"] else ""))
                          for s in srows]))

    out.append("\n## 4. 在聽 port 的程序（已排除系統服務）")
    out.append(table(["port", "類別", "pid", "啟動", "已開", "cwd", "父程序在", "Claude session"],
                     [(r["port"], r["cat"], r["pid"], fmt_time(r["start"]), fmt_age(r["age"]), r["cwd"],
                       "是" if r["parent_alive"] else "否", r["session"] or ("無（孤兒）" if r["orphan"] else "無"))
                      for r in ports]))

    if ctr.get("colima") or ctr.get("docker") or CONTAINER_NOTES:
        out.append("\n## 5. 容器／VM")
        out.extend("- %s" % n for n in CONTAINER_NOTES)
        if ctr.get("colima"):
            out.append("```\n%s\n```" % ctr["colima"])
        d = ctr.get("docker")
        if d:
            out.append(table(["容器", "記憶體"], [(n, fmt_mb(mb)) for n, mb in d["rows"]]))
            out.append("- 容器實際合計：%s（對照上面 colima 的 MEMORY 上限）" % fmt_mb(d["total_mb"]))

    out.append("\n## 6. 候選（建議；最後由 agent 判斷，關之前重讀狀態）")
    nodata = "資料不足，無法歸類（%s 失敗）" % "／".join(insufficient)
    out.append("\n### 可直接關")
    out.append(nodata if insufficient else table(["對象", "理由"], close))
    out.append("\n### 要問使用者")
    out.append(nodata if insufficient else table(["對象", "理由"], ask))
    out.append("\n### 不碰")
    out.append(nodata if insufficient else table(["對象", "理由"], keep))
    print("\n".join(out))


if __name__ == "__main__":
    main()
