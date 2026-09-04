#!/usr/bin/env python3
"""Find Claude Code sessions by topic keyword or by file-touch (Write/Edit path).

Usage:
  search.py --topic "spec skill" [--scope cwd|all|all-bak] [--output compact|graph|full]
  search.py --touched ~/.claude/skills/spec/SKILL.md
  search.py --topic foo --escalate         # cwd → all → all-bak until results found
  search.py --topic foo --since 2026-04-19 --until 2026-04-30 --limit 20

Notes:
  - --topic matches against user/assistant text and tool_use inputs, after stripping
    IDE/system wrappers and SKIPPING skill_listing attachments (huge source of false
    positives because the skill list contains every registered skill's description).
  - --touched matches Write / Edit / MultiEdit tool_use events whose file_path
    equals or ends with the given path. Use this to answer "who wrote X".
  - Sessions are de-duped by session UUID across .bak/non-bak project folders.
"""
from __future__ import annotations
import argparse, json, os, re, sys, glob
from pathlib import Path

PROJECTS_ROOT = Path.home() / ".claude" / "projects"

WRAPPERS = [
    re.compile(r"<ide_opened_file>.*?</ide_opened_file>", re.S),
    re.compile(r"<ide_selection>.*?</ide_selection>", re.S),
    re.compile(r"<system-reminder>.*?</system-reminder>", re.S),
    re.compile(r"<command-name>.*?</command-name>", re.S),
    re.compile(r"<command-message>.*?</command-message>", re.S),
    re.compile(r"<command-args>.*?</command-args>", re.S),
    re.compile(r"<local-command-stdout>.*?</local-command-stdout>", re.S),
    re.compile(r"<local-command-caveat>.*?</local-command-caveat>", re.S),
]


def cwd_project_dir(cwd: str | None = None) -> Path:
    """Translate a working directory to its Claude Code project folder name.

    `/Users/unilife/agent-skills` → `~/.claude/projects/-Users-unilife-agent-skills`.
    """
    cwd = cwd or os.getcwd()
    flat = cwd.replace("/", "-")
    return PROJECTS_ROOT / flat


def iter_session_files(scope: str, cwd: str | None = None):
    """Yield (session_id, jsonl_path) pairs honouring scope."""
    if scope == "cwd":
        roots = [cwd_project_dir(cwd)]
    else:
        roots = sorted(p for p in PROJECTS_ROOT.iterdir() if p.is_dir())
        if scope == "all":
            roots = [r for r in roots if not r.name.endswith(".bak")]
    seen: set[str] = set()
    for root in roots:
        if not root.exists():
            continue
        # top-level jsonls
        for f in sorted(root.glob("*.jsonl")):
            sid = f.stem
            if sid in seen:
                continue
            seen.add(sid)
            yield sid, f
        # subagent jsonls (under <sid>/subagents/*.jsonl)
        for f in sorted(root.glob("*/subagents/*.jsonl")):
            sid = f.stem
            if sid in seen:
                continue
            seen.add(sid)
            yield sid, f


def strip_wrappers(text: str) -> str:
    for rx in WRAPPERS:
        text = rx.sub("", text)
    return " ".join(text.split()).strip()


def extract_user_text(d: dict) -> str | None:
    """Return real user-typed text, or None for tool replies / wrappers-only / noise."""
    if d.get("type") != "user":
        return None
    m = d.get("message") or {}
    c = m.get("content", "")
    if isinstance(c, list):
        # tool_result-only turns are tool replies, not user input
        if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
            return None
        parts = [b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text"]
        text = "\n".join(parts)
    elif isinstance(c, str):
        text = c
    else:
        return None
    text = strip_wrappers(text)
    if not text:
        return None
    if text.startswith("[Request interrupted") or text.startswith("Caveat"):
        return None
    return text


def is_skill_listing(d: dict) -> bool:
    """Skip attachments that contain the system-injected skill list."""
    if d.get("type") != "attachment":
        return False
    att = d.get("attachment") or {}
    return att.get("type") == "skill_listing"


def scan_session(path: Path, topic: str | None, touched: str | None,
                 since: str | None, until: str | None) -> dict | None:
    """Scan one jsonl. Return a hit record or None.

    A hit means: at least one matching event AND timestamp is within [since,until].
    """
    if topic:
        topic_re = re.compile(re.escape(topic), re.I)
    else:
        topic_re = None
    touched_norm = os.path.expanduser(touched) if touched else None

    first_ts = last_ts = None
    first_user = None
    user_msgs: list[tuple[str, str]] = []
    topic_hits: list[tuple[str, str, str]] = []   # (ts, where, snippet)
    touch_hits: list[tuple[str, str, str]] = []   # (ts, tool, file_path)
    parent_uuids: set[str] = set()
    uuids: list[str] = []
    cwd = ""

    with path.open() as f:
        for line in f:
            try:
                d = json.loads(line)
            except Exception:
                continue
            ts = (d.get("timestamp") or "")[:19]
            if ts:
                first_ts = first_ts or ts
                last_ts = ts
            if not cwd and d.get("cwd"):
                cwd = d["cwd"]
            u = d.get("uuid")
            if u:
                uuids.append(u)
            p = d.get("parentUuid")
            if p:
                parent_uuids.add(p)

            # Real user message capture (for context / first-user / full output)
            ut = extract_user_text(d)
            if ut:
                if first_user is None:
                    first_user = ut
                user_msgs.append((ts, ut))

            # Topic search across user text + assistant text + tool_use inputs
            if topic_re:
                if is_skill_listing(d):
                    pass  # skip — false positive source
                else:
                    blob = ""
                    if d.get("type") in ("user", "assistant"):
                        m = d.get("message") or {}
                        c = m.get("content", "")
                        if isinstance(c, str):
                            blob = c
                        elif isinstance(c, list):
                            for b in c:
                                if not isinstance(b, dict):
                                    continue
                                if b.get("type") == "text":
                                    blob += "\n" + b.get("text", "")
                                elif b.get("type") == "tool_use":
                                    blob += "\n" + json.dumps(b.get("input", ""))
                    if blob and topic_re.search(blob):
                        # snippet around match
                        m_ = topic_re.search(blob)
                        s, e = max(0, m_.start() - 40), min(len(blob), m_.end() + 80)
                        topic_hits.append((ts, d.get("type", ""), blob[s:e]))

            # Touched-file search: tool_use Write/Edit/MultiEdit on the target path
            if touched_norm and d.get("type") == "assistant":
                m = d.get("message") or {}
                c = m.get("content", [])
                if isinstance(c, list):
                    for b in c:
                        if not isinstance(b, dict) or b.get("type") != "tool_use":
                            continue
                        nm = b.get("name", "")
                        if nm not in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
                            continue
                        inp = b.get("input") or {}
                        fp = inp.get("file_path", "")
                        if not fp:
                            continue
                        if fp == touched_norm or fp.endswith(touched_norm) or touched_norm.endswith(fp):
                            touch_hits.append((ts, nm, fp))

    if since and (last_ts or "") < since:
        return None
    if until and (first_ts or "9") > until:
        return None
    matched = bool(topic_hits) if topic else True
    if touched and not touch_hits:
        return None
    if topic and not matched:
        return None

    return {
        "session_id": path.stem,
        "path": str(path),
        "cwd": cwd,
        "first_ts": first_ts,
        "last_ts": last_ts,
        "first_user": first_user,
        "user_msgs": user_msgs,
        "topic_hits": topic_hits,
        "touch_hits": touch_hits,
        "uuids": uuids,
    }


def format_compact(hits: list[dict]) -> str:
    out = []
    for h in hits:
        first = (h["first_user"] or "").replace("\n", " ")[:120]
        out.append(f"{h['first_ts'] or '?':19s}  {h['session_id']}  {first}")
    return "\n".join(out)


def format_full(hits: list[dict], tail: int = 10) -> str:
    out = []
    for h in hits:
        out.append(f"\n=== {h['session_id']} ===")
        out.append(f"  span: {h['first_ts']} → {h['last_ts']}   cwd: {h['cwd']}")
        out.append(f"  path: {h['path']}")
        if h["touch_hits"]:
            out.append("  touched:")
            for ts, nm, fp in h["touch_hits"]:
                out.append(f"    [{ts}] {nm:10s} {fp}")
        if h["topic_hits"]:
            out.append(f"  topic matches: {len(h['topic_hits'])}")
            for ts, where, snip in h["topic_hits"][:3]:
                out.append(f"    [{ts}] ({where}) …{snip.strip()[:160]}…")
        if h["user_msgs"]:
            out.append(f"  last {min(tail, len(h['user_msgs']))} user msgs:")
            for ts, t in h["user_msgs"][-tail:]:
                out.append(f"    [{ts}] {t[:200]}")
    return "\n".join(out)


def format_graph(hits: list[dict]) -> str:
    """ASCII parent/fork graph using shared message-UUID detection."""
    hits = sorted(hits, key=lambda h: h["first_ts"] or "")
    uuid_sets = {h["session_id"]: set(h["uuids"]) for h in hits}
    parents: dict[str, str | None] = {}
    for h in hits:
        sid = h["session_id"]
        parent = None
        best_overlap = 0
        for other in hits:
            if other["session_id"] == sid:
                continue
            if (other["first_ts"] or "") > (h["first_ts"] or ""):
                continue
            overlap = len(uuid_sets[sid] & uuid_sets[other["session_id"]])
            if overlap > best_overlap:
                best_overlap = overlap
                parent = other["session_id"]
        parents[sid] = parent if best_overlap > 0 else None

    lines = []
    for h in hits:
        sid = h["session_id"]
        prefix = "  └─ " if parents[sid] else ""
        first = (h["first_user"] or "").replace("\n", " ")[:80]
        marker = f"(fork of {parents[sid][:8]})" if parents[sid] else ""
        lines.append(f"{h['first_ts'] or '?':19s}  {prefix}{sid[:8]}  {marker}  {first}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0] if __doc__ else None)
    ap.add_argument("--topic", help="keyword to search in user/assistant text and tool inputs")
    ap.add_argument("--touched", help="file path; match sessions that Wrote/Edited this file")
    ap.add_argument("--scope", choices=["cwd", "all", "all-bak"], default="cwd")
    ap.add_argument("--escalate", action="store_true",
                    help="if cwd finds 0, retry with all; if still 0, retry with all-bak")
    ap.add_argument("--output", choices=["compact", "graph", "full"], default="compact")
    ap.add_argument("--since", help="ISO date (YYYY-MM-DD)")
    ap.add_argument("--until", help="ISO date (YYYY-MM-DD)")
    ap.add_argument("--limit", type=int, default=0, help="0 = no limit")
    ap.add_argument("--cwd", help="override working directory for cwd-scope")
    args = ap.parse_args()

    if not args.topic and not args.touched:
        ap.error("provide --topic or --touched (or both)")

    scopes = [args.scope]
    if args.escalate:
        order = ["cwd", "all", "all-bak"]
        scopes = order[order.index(args.scope):]

    hits: list[dict] = []
    used_scope = args.scope
    for sc in scopes:
        hits = []
        for sid, path in iter_session_files(sc, args.cwd):
            try:
                rec = scan_session(path, args.topic, args.touched, args.since, args.until)
            except Exception as e:
                print(f"# error scanning {path}: {e}", file=sys.stderr)
                continue
            if rec:
                hits.append(rec)
        used_scope = sc
        if hits:
            break

    hits.sort(key=lambda h: h["first_ts"] or "")
    if args.limit:
        hits = hits[: args.limit]

    print(f"# scope={used_scope}  matches={len(hits)}")
    if not hits:
        return 1
    if args.output == "compact":
        print(format_compact(hits))
    elif args.output == "graph":
        print(format_graph(hits))
    else:
        print(format_full(hits))
    return 0


if __name__ == "__main__":
    sys.exit(main())
