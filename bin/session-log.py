#!/usr/bin/env python3
"""Per-session working memory: ~/.claude/projects/<proj>/<session-id>.log.md

One append-only, chronological file per session. Every line that starts a
record looks like `[MM-DD HH:MM tag] …`; a record runs until the next such
line. Tags: user assistant ask skill write error note compact.

Hook subcommands (read hook JSON on stdin, print nothing unless noted):
  snapshot   PreToolUse(Bash)         git status+hashes of watched repos -> tmp
  record     PostToolUse / PostToolUseFailure
             Write|Edit|MultiEdit|NotebookEdit -> [write]  path tool sha repo
             Bash  -> diff against snapshot   -> [write] per changed file
             Skill -> [skill];  failure event -> [error]
  said       Stop                     append [user]/[ask]/[assistant]/[compact] from transcript
  reprint    SessionStart(compact|resume)  said + print the whole log (stdout -> context)
  warn       PreToolUse(Write|Edit|MultiEdit|NotebookEdit)  another session wrote this file
             recently (its log has a [write] for the path) -> additionalContext warning
  index      SessionStart(startup|clear|fork)  the project's 5 most recent logs, 5 lines each
CLI:
  note "text"                          append [note] for the current session
  show [session-id]                    print the log
  writes [session-id]                  [write] paths grouped by repo, with dirty state (for wrap-up)
  export [session-id] [-o PATH]        readable transcript (user/assistant/ask only, secrets redacted)
  backfill --all | <session-id>        build/refresh logs from existing jsonl (one-off; Bash writes excluded)

Text extraction reuses skills/report/export-transcript.py (clean_text etc.).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECTS_ROOT = Path.home() / ".claude" / "projects"
TAGS = ("user", "assistant", "ask", "skill", "write", "error", "note", "compact")
RX_RECORD = re.compile(r"^\[(\d\d-\d\d \d\d:\d\d) (" + "|".join(TAGS) + r")\] ?(.*)$")
ABS = re.compile(r"(/(?:Users|home|private/tmp|tmp)/[^\s'\"`;|&<>(){}]+)")
REPRINT_MAX_TOKENS = 30_000
MAX_WATCH_REPOS = 6
MAX_HASH_FILES = 400


# ------------------------------------------------------------------ transcript
def _xt():
    """Lazy import of export-transcript.py (shares WRAPPERS / clean_text)."""
    p = HERE.parent / "skills" / "report" / "export-transcript.py"
    spec = importlib.util.spec_from_file_location("export_transcript", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------- paths
def log_path(hook: dict) -> Path | None:
    sid = hook.get("session_id")
    tp = hook.get("transcript_path") or ""
    if not sid:
        return None
    d = Path(tp).parent if tp else None
    if d and "subagents" in d.parts:
        d = d.parent.parent  # <proj>/<session>/subagents -> <proj>
    if not d or not d.is_dir():
        hits = sorted(PROJECTS_ROOT.glob(f"*/{sid}.jsonl"))
        d = hits[0].parent if hits else None
    return d / f"{sid}.log.md" if d else None


def state_path(lp: Path) -> Path:
    return lp.with_suffix(".state.json")


def load_state(lp: Path) -> dict:
    try:
        return json.loads(state_path(lp).read_text())
    except (OSError, ValueError):
        return {}


def save_state(lp: Path, st: dict) -> None:
    state_path(lp).write_text(json.dumps(st, ensure_ascii=False))


def snap_dir(hook: dict) -> Path:
    base = hook.get("scratchpad_dir") or f"/tmp/claude-session-log/{hook.get('session_id', 'x')}"
    d = Path(base) / ".session-log"
    d.mkdir(parents=True, exist_ok=True)
    return d


def stamp(ts: float | None = None) -> str:
    return time.strftime("%m-%d %H:%M", time.localtime(ts))


def header_line(lp: Path, title: str | None, cwd: str | None) -> str:
    sid = lp.stem.replace(".log", "")
    parts = [f"# {title}" if title else "# (untitled)", f"session {sid}"]
    if cwd:
        parts.append(cwd)
        branch = git(cwd, "branch", "--show-current").strip() if os.path.isdir(cwd) else ""
        if branch:
            parts.append(branch)
    return " · ".join(parts)


def ensure_header(lp: Path, title: str | None, cwd: str | None) -> None:
    """Line 1 is metadata (title · session · project · branch); rewrite it in place.
    Everything below stays append-only."""
    lp.parent.mkdir(parents=True, exist_ok=True)
    if not lp.exists():
        lp.write_text(header_line(lp, title, cwd) + "\n\n", encoding="utf-8")
        return
    text = lp.read_text(encoding="utf-8", errors="replace")
    first, _, rest = text.partition("\n")
    if not first.startswith("# "):
        lp.write_text(header_line(lp, title, cwd) + "\n\n" + text, encoding="utf-8")
        return
    if title is None:  # keep the title we already have
        m = re.match(r"# (.*?) · session ", first)
        if m and m.group(1) != "(untitled)":
            title = m.group(1)
    line = header_line(lp, title, cwd)
    if line != first:
        lp.write_text(line + "\n" + rest, encoding="utf-8")


def latest_title(entries: list[dict]) -> str | None:
    title = None
    for e in entries:
        if e.get("type") == "custom-title" and e.get("customTitle"):
            title = e["customTitle"]
    return title


def append(lp: Path, tag: str, body: str, ts: float | None = None) -> None:
    body = (body or "").rstrip()
    if not lp.exists():
        ensure_header(lp, None, None)
    with lp.open("a", encoding="utf-8") as fh:
        fh.write(f"[{stamp(ts)} {tag}] {body}\n")


def parse_log(lp: Path) -> list[dict]:
    recs: list[dict] = []
    if not lp.exists():
        return recs
    for line in lp.read_text(encoding="utf-8", errors="replace").splitlines():
        m = RX_RECORD.match(line)
        if m:
            recs.append({"ts": m.group(1), "tag": m.group(2), "body": m.group(3)})
        elif recs:
            recs[-1]["body"] += "\n" + line
    return recs


# ------------------------------------------------------------------------ git
def git(repo: str, *args: str, inp: str | None = None) -> str:
    r = subprocess.run(["git", "-C", repo, "-c", "core.quotepath=false", *args],
                       capture_output=True, text=True, input=inp)
    return r.stdout if r.returncode == 0 else ""


def repo_of(path: str) -> str | None:
    d = path if os.path.isdir(path) else os.path.dirname(path)
    if not os.path.isdir(d):
        return None
    top = git(d, "rev-parse", "--show-toplevel").strip()
    return os.path.realpath(top) if top else None


def dirty_files(repo: str) -> dict[str, str]:
    """relpath -> status code for every dirty/untracked file (files only)."""
    out: dict[str, str] = {}
    raw = git(repo, "status", "--porcelain", "-uall", "-z")
    parts = raw.split("\0")
    i = 0
    while i < len(parts):
        p = parts[i]
        i += 1
        if len(p) < 4:
            continue
        code, rel = p[:2], p[3:]
        if code[0] in "RC":  # renamed: next part is the original path
            i += 1
        out[rel] = code
    return out


def hash_files(repo: str, rels: list[str]) -> dict[str, str]:
    """relpath -> blob sha for existing files (batch)."""
    files = [r for r in rels if os.path.isfile(os.path.join(repo, r))]
    if not files:
        return {}
    if len(files) > MAX_HASH_FILES:  # degrade: mtime+size instead of content hash
        return {r: "stat:%d:%d" % (int(os.path.getmtime(os.path.join(repo, r))),
                                    os.path.getsize(os.path.join(repo, r))) for r in files}
    shas = git(repo, "hash-object", "--stdin-paths", inp="\n".join(files) + "\n").split()
    return dict(zip(files, shas))


def snapshot_repo(repo: str) -> dict[str, str]:
    """relpath -> sha (or 'D' for deleted) for every dirty file."""
    st = dirty_files(repo)
    shas = hash_files(repo, list(st))
    return {r: shas.get(r, "D") for r in st}


def blob_sha(path: str) -> str:
    try:
        data = Path(path).read_bytes()
    except OSError:
        return "-"
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()[:12]


def est_tokens(text: str) -> int:
    """Rough token count: a CJK character ≈ 1 token, anything else ≈ 4 chars/token."""
    cjk = sum(1 for ch in text if "　" <= ch <= "鿿" or "＀" <= ch <= "￯")
    return cjk + (len(text) - cjk) // 4


def short(sha: str) -> str:
    return sha if sha in ("D", "-") or sha.startswith("stat:") else sha[:12]


# ------------------------------------------------------------------ watching
def watch_repos(hook: dict, lp: Path) -> list[str]:
    repos: list[str] = []

    def add(r: str | None) -> None:
        if r and r not in repos and len(repos) < MAX_WATCH_REPOS:
            repos.append(r)

    add(repo_of(hook.get("cwd") or os.getcwd()))
    cmd = (hook.get("tool_input") or {}).get("command") or ""
    for raw in ABS.findall(cmd):
        add(repo_of(raw.rstrip(".,:")))
    for rec in parse_log(lp):
        if rec["tag"] == "write":
            m = re.search(r"\brepo=(\S+)", rec["body"])
            if m and m.group(1) != "-":
                add(m.group(1))
    return repos


# User-role entries the harness writes itself (not the human). Dropped from [user].
HARNESS_USER = (
    "Another Claude session sent a message",
    "[SYSTEM NOTIFICATION",
    "<task-notification>",
    "The user hasn't heard from you in a while",
    "[Request interrupted",
    "Your questions have been answered",  # logged via [ask] from the tool_result instead
)
RX_MIDTURN = re.compile(
    r"^The user sent a new message while you were working:\s*(.*?)\s*"
    r"(?:This is how Claude Code surfaces messages.*)?$", re.S)


def human_text(text: str) -> str:
    """Cleaned human text of a user entry, or '' when the harness wrote it."""
    t = text.strip()
    m = RX_MIDTURN.match(t)
    if m:
        t = m.group(1).strip()
    if any(t.startswith(p) for p in HARNESS_USER):
        return ""
    return t


def agent_suffix(hook: dict) -> str:
    aid = hook.get("agent_id")
    return f" agent={aid[:8]}" if aid else ""


# -------------------------------------------------------------- subcommands
def cmd_snapshot(hook: dict) -> None:
    lp = log_path(hook)
    if not lp:
        return
    snap = {r: snapshot_repo(r) for r in watch_repos(hook, lp)}
    key = hook.get("tool_use_id") or "latest"
    (snap_dir(hook) / f"{key}.json").write_text(json.dumps(snap))


def record_write(lp: Path, hook: dict, path: str, tool: str, sha: str | None = None) -> None:
    repo = repo_of(path) or "-"
    if sha is None:
        if repo != "-" and os.path.isfile(path):
            rel = os.path.relpath(os.path.realpath(path), repo)
            sha = hash_files(repo, [rel]).get(rel, blob_sha(path))
        else:
            sha = blob_sha(path) if os.path.isfile(path) else "D"
    append(lp, "write", f"{path} tool={tool} sha={short(sha)} repo={repo}{agent_suffix(hook)}")


def cmd_record(hook: dict) -> None:
    lp = log_path(hook)
    if not lp:
        return
    tool = hook.get("tool_name") or "?"
    inp = hook.get("tool_input") or {}

    if hook.get("hook_event_name") == "PostToolUseFailure":
        err = (hook.get("error") or "").strip().splitlines()
        head = err[0][:200] if err else "(no message)"
        what = inp.get("command") or inp.get("file_path") or inp.get("skill") or ""
        what = re.sub(r"\s+", " ", str(what))[:120]
        append(lp, "error", f"tool={tool} {what}\n  {head}{agent_suffix(hook)}")
        return

    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        p = inp.get("file_path") or inp.get("notebook_path")
        if p:
            record_write(lp, hook, p, tool)
        return

    if tool == "Skill":
        append(lp, "skill", f"{inp.get('skill', '?')} {inp.get('args') or ''}".rstrip())
        return

    if tool == "Bash":
        key = hook.get("tool_use_id") or "latest"
        sp = snap_dir(hook) / f"{key}.json"
        try:
            before = json.loads(sp.read_text())
        except (OSError, ValueError):
            return  # no pre-snapshot: cannot attribute, record nothing (never guess)
        try:
            sp.unlink()
        except OSError:
            pass
        for repo in watch_repos(hook, lp):
            after = snapshot_repo(repo)
            prev = before.get(repo, {})
            for rel, sha in after.items():
                if prev.get(rel) != sha:
                    record_write(lp, hook, os.path.join(repo, rel), "Bash", sha)
            for rel in prev:
                if rel not in after and os.path.isfile(os.path.join(repo, rel)):
                    # was dirty, now clean: committed or reverted by this command
                    record_write(lp, hook, os.path.join(repo, rel), "Bash", "clean")


def _turns_from_transcript(hook: dict, lp: Path, st: dict) -> list[tuple[str, str, float | None]]:
    """(tag, body, ts) records not yet logged, in transcript order."""
    xt = _xt()
    tp = hook.get("transcript_path") or ""
    if not os.path.isfile(tp):
        return []
    entries = xt.read_entries(Path(tp))
    ensure_header(lp, hook.get("session_title") or latest_title(entries), hook.get("cwd"))
    names = xt.tool_name_map(entries)
    # Backfill: tool events before the hooks existed are not in the log (record
    # only sees live calls). Re-derive Write/Edit/Skill/error from the transcript
    # for entries older than the moment this log started; Bash writes are NOT
    # backfilled (no snapshot then → would be a guess).
    hook_since = st.setdefault("hook_since", time.time())
    tools = {b.get("id"): (b.get("name"), b.get("input") or {})
             for e in entries for b in xt.blocks_of(((e.get("message") or {}).get("content")))
             if isinstance(b, dict) and b.get("type") == "tool_use"}
    have_writes = {(r["body"].split(" ", 1)[0], r["ts"]) for r in parse_log(lp) if r["tag"] == "write"}
    done = set(st.get("seen", []))
    out: list[tuple[str, str, float | None]] = []
    pending_assistant: tuple[str, str, float | None] | None = None
    seen_texts = set(st.get("assistant_hashes", []))

    def flush_assistant() -> None:
        # Emit the turn's LAST assistant text, and only if not logged before.
        # Earlier texts of the same turn are dropped even when unseen, so a
        # later run can't resurface an interstitial one-liner out of order.
        nonlocal pending_assistant
        if pending_assistant:
            h = hashlib.sha1(pending_assistant[1].encode()).hexdigest()[:16]
            if h not in seen_texts:
                out.append(pending_assistant)
            pending_assistant = None

    def ts_of(e: dict) -> float | None:
        dt = xt.parse_ts(e.get("timestamp"))
        return dt.timestamp() if dt else None

    for e in entries:
        uid = e.get("uuid")
        if e.get("isSidechain"):
            continue
        et = e.get("type")
        if et == "system" and e.get("subtype") == "compact_boundary":
            if uid not in done:
                flush_assistant()
                out.append(("compact", xt.compact_note(e).strip("_"), ts_of(e)))
                done.add(uid)
            continue
        if et == "attachment":
            att = e.get("attachment") or {}
            if att.get("type") == "queued_command" and (att.get("origin") or {}).get("kind") == "human" \
                    and att.get("commandMode") == "prompt" and uid not in done:
                prompt = att.get("prompt")
                text = xt.clean_text(prompt if isinstance(prompt, str) else "\n\n".join(
                    b.get("text", "") for b in prompt or [] if isinstance(b, dict)))
                if text:
                    flush_assistant()
                    out.append(("user", text, ts_of(e)))
                done.add(uid)
            continue
        if et not in ("user", "assistant"):
            continue
        msg = e.get("message") or {}
        blocks = xt.blocks_of(msg.get("content"))
        if et == "user":
            if e.get("isMeta") or e.get("isCompactSummary"):
                continue
            texts, asks = [], []
            for b in blocks:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "text":
                    t = human_text(xt.clean_text(b.get("text", "")))
                    if t:
                        texts.append(t)
                elif b.get("type") == "tool_result" and b.get("is_error") and uid not in done \
                        and (ts_of(e) or 0) < hook_since:
                    name, inp = tools.get(b.get("tool_use_id"), ("?", {}))
                    what = re.sub(r"\s+", " ", str(inp.get("command") or inp.get("file_path") or inp.get("skill") or ""))[:120]
                    head = (xt.result_to_text(b).strip().splitlines() or ["(no message)"])[0][:200]
                    out.append(("error", f"tool={name} {what}\n  {head}", ts_of(e)))
                    done.add(uid)
                elif b.get("type") == "tool_result" and names.get(b.get("tool_use_id")) == "AskUserQuestion":
                    body = xt.RX_ASK_TAIL.sub("", xt.result_to_text(b).strip())
                    body = re.sub(r"^Your questions have been answered:\s*", "", body)
                    if body:
                        asks.append(body)
            if (texts or asks) and uid not in done:
                flush_assistant()  # a human turn ends the previous assistant turn
                for t in texts:
                    out.append(("user", t, ts_of(e)))
                for a in asks:
                    out.append(("ask", a, ts_of(e)))
            if texts or asks:
                done.add(uid)
            continue
        # assistant tool_use before the hooks existed → backfill [write]/[skill]
        if uid not in done and (ts_of(e) or 0) < hook_since:
            for b in blocks:
                if not isinstance(b, dict) or b.get("type") != "tool_use":
                    continue
                name, inp = b.get("name"), b.get("input") or {}
                if name in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
                    path = inp.get("file_path") or inp.get("notebook_path")
                    if path and (path, stamp(ts_of(e))) not in have_writes:
                        out.append(("write", f"{path} tool={name} sha=? repo={repo_of(path) or '-'}", ts_of(e)))
                        done.add(uid)
                elif name == "Skill":
                    out.append(("skill", f"{inp.get('skill', '?')} {inp.get('args') or ''}".rstrip(), ts_of(e)))
                    done.add(uid)
        # assistant: keep only the last text of the turn
        t = "\n\n".join(xt.clean_text(b.get("text", "")) for b in blocks
                        if isinstance(b, dict) and b.get("type") == "text").strip()
        if t:
            pending_assistant = ("assistant", t, ts_of(e))
    flush_assistant()

    lam = (hook.get("last_assistant_message") or "").strip()
    if lam:
        h = hashlib.sha1(lam.encode()).hexdigest()[:16]
        if h not in seen_texts and not any(tag == "assistant" and body == lam for tag, body, _ in out):
            out.append(("assistant", lam, None))

    # remember what we emitted
    for tag, body, _ in out:
        if tag == "assistant":
            seen_texts.add(hashlib.sha1(body.encode()).hexdigest()[:16])
    st["seen"] = sorted(done)[-5000:]
    st["assistant_hashes"] = sorted(seen_texts)[-2000:]
    return out


def cmd_said(hook: dict) -> None:
    lp = log_path(hook)
    if not lp:
        return
    st = load_state(lp)
    recs = _turns_from_transcript(hook, lp, st)
    # The jsonl is not strictly chronological (a `/compact` command line is written
    # after the compact_boundary it caused), so order this batch by timestamp.
    recs.sort(key=lambda r: r[2] if r[2] is not None else float("inf"))
    for tag, body, ts in recs:
        append(lp, tag, body, ts)
    save_state(lp, st)


def render_reprint(lp: Path, hook: dict) -> str:
    recs = parse_log(lp)
    if not recs:
        return ""
    total = sum(est_tokens(r["body"]) for r in recs)
    if total > REPRINT_MAX_TOKENS:
        for r in recs:  # oldest assistant bodies first
            if r["tag"] == "assistant" and total > REPRINT_MAX_TOKENS:
                first = r["body"].splitlines()[0] if r["body"] else ""
                total -= est_tokens(r["body"]) - est_tokens(first)
                r["body"] = first + f"  …(截斷，全文見 {lp.name})"
    head = lp.read_text(encoding="utf-8", errors="replace").partition("\n")[0]
    lines = [f"[session-log] 本 session 的工作紀錄（來自 transcript／git，不是摘要）：{lp}", head]
    for r in recs:
        lines.append(f"[{r['ts']} {r['tag']}] {r['body']}")

    # derived state: uncommitted files this session wrote, session commits
    sid = lp.stem.replace(".log", "")
    table = uncommitted_writes(lp)
    repos = sorted({re.search(r"repo=(\S+)", r["body"]).group(1) for r in recs
                    if r["tag"] == "write" and re.search(r"repo=(\S+)", r["body"])} - {"-"})
    if table:
        lines.append("")
        lines.append("== 本 session 寫過、仍未 commit 的檔 ==")
        for repo, rows in table.items():
            lines.append(repo)
            lines.extend(rows)
    if repos:
        lines.append("")
        lines.append("== 本 session 的 commit ==")
        for repo in repos:
            log = git(repo, "log", f"--grep={sid}", "-n", "10", "--format=%h %ad %s", "--date=short").strip()
            if log:
                lines.append(repo)
                lines.extend("  " + l for l in log.splitlines())
    return "\n".join(lines)


def cmd_reprint(hook: dict) -> None:
    lp = log_path(hook)
    if not lp:
        return
    cmd_said(hook)
    out = render_reprint(lp, hook)
    if out:
        print(out)


WARN_WINDOW_S = 48 * 3600


def cmd_warn(hook: dict) -> None:
    inp = hook.get("tool_input") or {}
    path = inp.get("file_path") or inp.get("notebook_path")
    if not path:
        return
    target = os.path.realpath(path)
    me = hook.get("session_id") or ""
    now = time.time()
    hits: list[str] = []
    for lp in PROJECTS_ROOT.glob("*/*.log.md"):
        if lp.name.startswith(me) or now - lp.stat().st_mtime > WARN_WINDOW_S:
            continue
        last = None
        for r in parse_log(lp):
            if r["tag"] == "write" and r["body"].split(" ", 1)[0] and \
                    os.path.realpath(r["body"].split(" ", 1)[0]) == target:
                last = r
        if not last:
            continue
        title = lp.read_text(encoding="utf-8", errors="replace").partition("\n")[0].lstrip("# ").split(" · ")[0]
        sha = re.search(r"sha=(\S+)", last["body"])
        cur = short(hash_files(repo_of(target) or "/", [os.path.relpath(target, repo_of(target))]).get(
            os.path.relpath(target, repo_of(target)), "-")) if repo_of(target) else "-"
        same = sha and sha.group(1) == cur
        hits.append(f"- session {lp.stem.replace('.log', '')[:8]}「{title}」於 {last['ts']} 寫過此檔"
                    + ("（磁碟上現在就是它寫的版本）" if same else "（之後又被改過）"))
    if not hits:
        return
    ctx = (f"[session-log] 另一個 session 最近寫過 {path}：\n" + "\n".join(hits)
           + "\n寫入前先重讀現況、只做加法編輯；commit 時這個檔要用 pathspec／hash-object 拆。")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": ctx}},
                     ensure_ascii=False))


INDEX_N = 5


def _one_line(text: str, n: int = 90) -> str:
    t = " ".join(text.split())
    return t if len(t) <= n else t[:n] + "…"


def cmd_index(hook: dict) -> None:
    """Print the project's most recent session logs so a new session can pull the
    one it needs instead of the user pasting it."""
    me = hook.get("session_id") or ""
    tp = hook.get("transcript_path") or ""
    proj = Path(tp).parent if tp else Path(os.path.expanduser("~/.claude/projects")) / (hook.get("cwd") or os.getcwd()).replace("/", "-")
    if not proj.is_dir():
        return
    logs = sorted((p for p in proj.glob("*.log.md") if not p.name.startswith(me)),
                  key=lambda p: p.stat().st_mtime, reverse=True)[:INDEX_N]
    if not logs:
        return
    now = time.time()
    out = [f"[session-log] 這個專案最近 {len(logs)} 個 session 的工作紀錄（要接手哪個就讀那個路徲，或用 find-session）："]
    for lp in logs:
        recs = parse_log(lp)
        head = lp.read_text(encoding="utf-8", errors="replace").partition("\n")[0]
        if not recs:
            out += ["", head, f"  {lp}"]
            continue
        tags = [r["tag"] for r in recs]
        writes = [r for r in recs if r["tag"] == "write"]
        dirty = sum(len(v) for v in uncommitted_writes(lp).values()) if writes else 0
        age = now - lp.stat().st_mtime
        state = "活躍中" if age < 600 else f"閒置 {int(age // 3600)}h" if age >= 3600 else f"閒置 {int(age // 60)}m"
        last_note = next((r for r in reversed(recs) if r["tag"] == "note"), None)
        last_user = next((r for r in reversed(recs) if r["tag"] == "user"), None)
        out += ["", head,
                f"  {recs[0]['ts']} → {recs[-1]['ts']} · user {tags.count('user')} · write {len(writes)}"
                f"（未 commit {dirty}）· error {tags.count('error')} · {state}"]
        if last_note:
            out.append(f"  [note] {_one_line(last_note['body'])}")
        if last_user:
            out.append(f"  [user] {_one_line(last_user['body'])}")
        out.append(f"  {lp}")
    print("\n".join(out))


def cmd_note(text: str) -> None:
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if not sid:
        sys.exit("CLAUDE_CODE_SESSION_ID not set")
    lp = log_path({"session_id": sid})
    if not lp:
        sys.exit(f"no transcript dir for session {sid}")
    append(lp, "note", text)


def _cli_log(sid: str | None) -> Path:
    sid = sid or os.environ.get("CLAUDE_CODE_SESSION_ID")
    lp = log_path({"session_id": sid}) if sid else None
    if not lp or not lp.exists():
        sys.exit(f"no session log for {sid or '(no session id)'}; older sessions only have the jsonl")
    return lp


def cmd_show(sid: str | None) -> None:
    sys.stdout.write(_cli_log(sid).read_text())


def uncommitted_writes(lp: Path) -> dict[str, list[str]]:
    """repo -> lines describing this session's still-dirty files."""
    writes: dict[str, dict] = {}
    for r in parse_log(lp):
        if r["tag"] != "write":
            continue
        m = re.match(r"(\S+) tool=(\S+) sha=(\S+) repo=(\S+)", r["body"])
        if m:
            writes[m.group(1)] = {"sha": m.group(3), "repo": m.group(4)}
    out: dict[str, list[str]] = {}
    by_repo: dict[str, list[str]] = {}
    for p, w in writes.items():
        if w["repo"] != "-":
            by_repo.setdefault(w["repo"], []).append(p)
    for repo, paths in sorted(by_repo.items()):
        dirty = dirty_files(repo)
        rows = []
        for p in sorted(paths):
            rel = os.path.relpath(os.path.realpath(p), repo)
            if rel not in dirty:
                continue
            cur = hash_files(repo, [rel]).get(rel, "D")
            if writes[p]["sha"] == "?":
                mark = "hook 前寫的，無法比對是否被改"
            else:
                mark = "我寫的，之後沒人動" if short(cur) == writes[p]["sha"] else "我寫過，之後被改（可能有別的 session 的 hunk）"
            rows.append(f"  {dirty[rel]} {rel}  ← {mark}")
        if rows:
            out[repo] = rows
    return out


def cmd_writes(sid: str | None) -> None:
    lp = _cli_log(sid)
    table = uncommitted_writes(lp)
    if not table:
        print("(no uncommitted files written by this session)")
        return
    for repo, rows in table.items():
        print(f"{repo}  ({len(rows)} uncommitted)")
        print("\n".join(rows))


# Secrets never leave the machine in an export. Conservative patterns; a false
# positive only hides a token-looking string, a miss leaks a credential.
SECRET_RX = [
    re.compile(r"(?i)\b(sk|pk|rk|ak|ghp|gho|xox[abp]|AKIA|AIza|ya29)[-_][A-Za-z0-9_\-]{12,}"),
    re.compile(r"(?i)\b(eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,})"),  # JWT
    re.compile(r"(?i)\b(api[_-]?key|secret|token|password|passwd|pwd)\b\s*[:=]\s*['\"]?([^\s'\"]{6,})"),
    re.compile(r"(?i)(postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp)://[^\s'\"]+:[^\s'\"@]+@"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
]


def redact(text: str) -> str:
    for rx in SECRET_RX:
        text = rx.sub(lambda m: (m.group(1) + "=[REDACTED]") if m.lastindex and m.lastindex >= 2
                      and m.re is SECRET_RX[2] else "[REDACTED]", text)
    return text


HEADS = {"user": "## 👤 User", "assistant": "## 🤖 Assistant", "ask": "## 👤 User (answered)",
         "compact": "## ⤵ Context compacted", "note": "## 📝 Note"}


def cmd_export(argv: list[str]) -> None:
    out_path = None
    sid = None
    it = iter(argv)
    for a in it:
        if a == "-o":
            out_path = next(it, None)
        else:
            sid = a
    lp = _cli_log(sid)
    head = lp.read_text(encoding="utf-8", errors="replace").partition("\n")[0]
    lines = [head.lstrip("# ").split(" · ")[0] and "# " + head.lstrip("# ").split(" · ")[0], "",
             f"- {head.lstrip('# ')}", f"- Exported: {time.strftime('%Y-%m-%d %H:%M')} from {lp.name}", "", "---", ""]
    for r in parse_log(lp):
        if r["tag"] not in HEADS:
            continue
        lines.append(f"{HEADS[r['tag']]}  ·  {r['ts']}")
        lines.append("")
        lines.append(redact(r["body"]))
        lines.append("")
    text = "\n".join(lines).rstrip() + "\n"
    if out_path:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(text, encoding="utf-8")
        print(out_path)
    else:
        sys.stdout.write(text)


def cmd_backfill(arg: str | None) -> None:
    if arg == "--all":
        files = sorted(PROJECTS_ROOT.glob("*/*.jsonl"))
    elif arg:
        files = sorted(PROJECTS_ROOT.glob(f"*/{arg}.jsonl"))
    else:
        sys.exit("backfill --all | <session-id>")
    n = 0
    for tp in files:
        if tp.name.endswith(".log.md") or ".orphaned-" in tp.name or ".superseded-" in tp.name:
            continue
        hook = {"session_id": tp.stem, "transcript_path": str(tp)}
        try:
            cmd_said(hook)
            n += 1
        except Exception as exc:  # keep going; one bad transcript must not stop the batch
            sys.stderr.write(f"backfill {tp.name}: {exc}\n")
    print(f"backfilled {n} sessions")


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        sys.exit(__doc__)
    sub = argv[1]
    if sub == "note":
        cmd_note(" ".join(argv[2:]))
        return
    if sub == "show":
        cmd_show(argv[2] if len(argv) > 2 else None)
        return
    if sub == "writes":
        cmd_writes(argv[2] if len(argv) > 2 else None)
        return
    if sub == "export":
        cmd_export(argv[2:])
        return
    if sub == "backfill":
        cmd_backfill(argv[2] if len(argv) > 2 else None)
        return
    try:
        hook = json.load(sys.stdin)
    except ValueError:
        return
    try:
        {"snapshot": cmd_snapshot, "record": cmd_record, "said": cmd_said,
         "reprint": cmd_reprint, "warn": cmd_warn, "index": cmd_index}[sub](hook)
    except KeyError:
        sys.exit(f"unknown subcommand {sub}")
    except Exception as exc:  # never break the session over a logging failure
        sys.stderr.write(f"session-log {sub}: {exc}\n")


if __name__ == "__main__":
    main(sys.argv)
