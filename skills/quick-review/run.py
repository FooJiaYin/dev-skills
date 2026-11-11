#!/usr/bin/env python3
"""quick-review: two-round Codex review of the uncommitted diff -> REVIEW.md.

Round 1: `codex exec review --uncommitted` with no checklist (free judgment).
Round 2: resume the same Codex thread with shared/review/commons.md (+ the
repo's docs/review-standard.md) and ask only for findings not already reported.

Exit codes: 0 = REVIEW.md written; 3 = Codex unavailable or running on a Codex
host (caller uses the agent fallback in SKILL.md); 4 = REVIEW.md written but the
checklist round (or a --from-text round) did not complete (status: incomplete); 2 = error.
Stdlib only. Never edits source files except REVIEW.md and .gitignore.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
DEV_SKILLS_ROOT = SKILL_DIR.parent.parent
COMMONS = DEV_SKILLS_ROOT / "shared" / "review" / "commons.md"
ADAPTER = DEV_SKILLS_ROOT / "bin" / "session-adapter.py"
NVM_BIN = Path.home() / ".nvm" / "versions" / "node" / "v24.22.1" / "bin"
CODEX_TIMEOUT = 1800

SEVERITY = {"P0": "Critical", "P1": "Critical", "P2": "Warning", "P3": "Suggestion"}
PREFIX = {"Critical": "CR", "Warning": "WR", "Suggestion": "SG", "Nit": "NT"}
ORDER = ["Critical", "Warning", "Suggestion", "Nit"]

# `- [P1] Title — path/to/file.py:12` (also accepts `-` / `–` as separator, `:12-15` ranges)
FINDING_RE = re.compile(
    r"^\s*(?:[-*]|\d+\.)?\s*\*{0,2}\[(P[0-3])\]\*{0,2}\s*(.+?)\s+[—–-]+\s+`?([^\s`]+?)(?::(\d+)(?:-\d+)?)?`?\s*$"
)
NO_FINDINGS_RE = re.compile(r"\bno (new )?(findings|issues)\b|looks good|lgtm", re.I)
FINDING_NOLOC_RE =re.compile(r"^\s*(?:[-*]|\d+\.)?\s*\*{0,2}\[(P[0-3])\]\*{0,2}\s*(.+?)\s*$")


def log(msg: str) -> None:
    print(f"[quick-review] {msg}", file=sys.stderr)


def run(cmd: list[str], cwd: Path | None = None, env: dict | None = None,
        timeout: int | None = None, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, env=env, timeout=timeout, input=stdin,
                          capture_output=True, text=True)


def git(root: Path, *args: str) -> str:
    return run(["git", *args], cwd=root).stdout


def find_codex() -> tuple[str | None, dict]:
    env = os.environ.copy()
    found = shutil.which("codex")
    if not found and (NVM_BIN / "codex").exists():
        found = str(NVM_BIN / "codex")
    if found and NVM_BIN.is_dir():
        # codex is a node script; make sure its node is reachable too
        env["PATH"] = f"{NVM_BIN}{os.pathsep}{env.get('PATH', '')}"
    return found, env


def changed_files(root: Path, base: str | None = None) -> list[str]:
    out = run(["git", "status", "--porcelain", "-z", "--untracked-files=all"], cwd=root).stdout
    files, entries, i = [], out.split("\0"), 0
    if base:  # already-committed session work: base..HEAD plus whatever is still dirty
        # -z keeps non-ASCII paths literal (default output quotes and escapes them)
        files += [f for f in git(root, "diff", "--name-only", "-z", f"{base}..HEAD").split("\0") if f]
    while i < len(entries):
        entry = entries[i]
        i += 1
        if len(entry) < 4:
            continue
        status, path = entry[:2], entry[3:]
        if status[0] in "RC":  # rename/copy: next entry is the old path
            i += 1
        if path and not re.fullmatch(r"REVIEW(-\w+)?\.md", path) and path not in files:
            files.append(path)
    return files


def changed_lines(root: Path, rel: str, base: str | None, cached: bool = False) -> set[int] | None:
    """Changed line numbers of a file vs base (or HEAD); None = whole file (new/untracked).
    cached=True diffs the staged (index) version instead of the working file."""
    proc = run(["git", "diff", "-U0", *(["--cached"] if cached else []), base or "HEAD", "--", rel],
               cwd=root)
    if proc.returncode != 0:
        return None
    if not proc.stdout.strip():
        # no diff: a file tracked at base/HEAD is unchanged (nothing in scope); otherwise it's new
        known = run(["git", "cat-file", "-e", f"{base or 'HEAD'}:{rel}"], cwd=root).returncode == 0
        return set() if known else None
    lines: set[int] = set()
    for m in re.finditer(r"^@@ -\S+ \+(\d+)(?:,(\d+))? @@", proc.stdout, re.M):
        start, count = int(m.group(1)), int(m.group(2) or 1)
        lines.update(range(start, start + count))
    return lines


# ---------------------------------------------------------------- secret scan

def secret_scan(root: Path, files: list[str], base: str | None = None) -> tuple[str, list[dict]]:
    """Return (secret_scan status, findings on changed lines only). Never raises."""
    if not shutil.which("gitleaks"):
        return "skipped", []
    findings: list[dict] = []
    try:
        with tempfile.TemporaryDirectory() as tmp:
            targets = []  # (rel, file to scan, staged?)
            for idx, rel in enumerate(files):
                path = root / rel
                if path.is_file():
                    targets.append((rel, path, False))
                # the staged blob is what gets committed; scan it when it differs from the working file
                # bytes, not text: staged binaries (PNG…) must not break the scan
                staged = subprocess.run(["git", "show", f":{rel}"], cwd=root, capture_output=True)
                if staged.returncode == 0 and (not path.is_file() or staged.stdout != path.read_bytes()):
                    blob = Path(tmp) / f"staged{idx}{path.suffix}"
                    blob.write_bytes(staged.stdout)
                    targets.append((rel, blob, True))
            seen: set[tuple] = set()
            for idx, (rel, path, is_staged) in enumerate(targets):
                report = Path(tmp) / f"r{idx}.json"
                proc = run(["gitleaks", "detect", "--no-git", "--no-banner", "--redact",
                            "--source", str(path), "--report-format", "json",
                            "--report-path", str(report)], cwd=root, timeout=120)
                if proc.returncode not in (0, 1):
                    log(f"gitleaks failed on {rel}: {proc.stderr.strip()[:200]}")
                    return "error", findings
                if proc.returncode == 1 and report.exists():
                    touched = changed_lines(root, rel, base, cached=is_staged)
                    for leak in json.loads(report.read_text() or "[]"):
                        if touched is not None and leak.get("StartLine") not in touched:
                            continue  # pre-existing secret on an untouched line
                        if (rel, leak.get("StartLine"), leak.get("RuleID")) in seen:
                            continue
                        seen.add((rel, leak.get("StartLine"), leak.get("RuleID")))
                        findings.append({
                            "severity": "Critical",
                            "title": f"Secret detected ({leak.get('RuleID') or leak.get('Description') or 'gitleaks'})",
                            "path": rel,
                            "line": leak.get("StartLine"),
                            "body": f"gitleaks rule `{leak.get('RuleID')}` matched a value on this line "
                                    "(redacted). Move it to env / Keychain / Secret Manager and rotate it "
                                    "if it was ever pushed.",
                        })
    except Exception as exc:  # noqa: BLE001 - scan must never break the review
        log(f"gitleaks error: {exc}")
        return "error", findings
    return ("found" if findings else "clean"), findings


# ---------------------------------------------------------------- codex

def parse_jsonl(text: str) -> tuple[str | None, str]:
    """Return (thread_id, last agent message text) from `codex exec --json` output."""
    thread_id, last_msg = None, ""
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        etype = str(event.get("type", ""))
        if thread_id is None and (etype.endswith("started") or "thread_id" in event):
            thread_id = event.get("thread_id") or (event.get("thread") or {}).get("id") or thread_id
        item = event.get("item") or {}
        if item.get("type") in ("agent_message", "assistant_message") and item.get("text"):
            last_msg = item["text"]
    return thread_id, last_msg


def codex_exec(codex: str, env: dict, root: Path, args: list[str]) -> tuple[str | None, str]:
    proc = run([codex, "exec", *args, "--json"], cwd=root, env=env, timeout=CODEX_TIMEOUT,
               stdin="")
    thread_id, msg = parse_jsonl(proc.stdout)
    if proc.returncode != 0 or not msg.strip():
        # a non-zero exit may still carry progress chatter; never treat it as a finished review
        raise RuntimeError(f"codex exec {args[0]} exited {proc.returncode} "
                           f"({'no final message' if not msg.strip() else 'interrupted'}): "
                           f"{(proc.stderr or proc.stdout).strip()[-500:]}")
    return thread_id, msg


def origin_session() -> tuple[str | None, str | None]:
    """(id, title) of the session running this review. Never raises."""
    try:
        proc = run([sys.executable, str(ADAPTER), "show", "--json"], timeout=60)
        if proc.returncode == 0:
            meta = json.loads(proc.stdout)
            name = (meta.get("name") or "").strip()
            return (str(meta.get("id") or "") or None,
                    name if name and name != "(untitled)" else None)
    except Exception as exc:  # noqa: BLE001
        log(f"could not read origin session: {exc}")
    return os.environ.get("CLAUDE_CODE_SESSION_ID"), None


def name_thread(thread_id: str, origin: str | None, title: str | None, env: dict) -> str:
    """Rename the Codex thread after the origin session. Never raises."""
    id8 = (origin or thread_id)[:8]
    label = f"quick-review ← {title} ({id8})" if title else f"quick-review ← {id8}"
    try:
        # env carries the nvm PATH: the adapter shells out to `codex app-server`
        proc = run([sys.executable, str(ADAPTER), "rename", "--host", "codex",
                    "--session", thread_id, label], env=env, timeout=60)
        if proc.returncode != 0:
            log(f"rename failed (ignored): {(proc.stderr or proc.stdout).strip()[:200]}")
    except Exception as exc:  # noqa: BLE001
        log(f"rename failed (ignored): {exc}")
    return label


def round2_prompt(root: Path, files: list[str] | None, base: str | None = None) -> str:
    if COMMONS.is_file():
        parts = [COMMONS.read_text()]
    else:  # skill installed without the repo-level shared/ folder
        log(f"commons not found at {COMMONS}; checklist round uses the project standard only")
        parts = ["# Review commons missing\n\nApply basic engineering standards and a security "
                 "pass (secrets, injection, authorization, XSS, server-only values on the client)."]
    standard = root / "docs" / "review-standard.md"
    if standard.is_file():
        parts.append("# Project review standard (wins over the commons on conflict)\n\n"
                     + standard.read_text())
    scope = ""
    if files:
        scope = ("\nOnly review these files (other uncommitted files belong to another "
                 "session):\n" + "\n".join(f"- {f}" for f in files) + "\n")
    parts.append(
        "# Task\n\n"
        f"Re-check the same diff ({f'{base}..HEAD plus uncommitted changes' if base else 'uncommitted changes'}) "
        "against the checklist above. Report ONLY findings "
        "that are NOT already in your previous review. Comment only on changed lines.\n"
        f"{scope}\n"
        "Output format, exactly (nothing else; write `No new findings.` if there are none):\n\n"
        "- [P0-P3] <short title> — <repo-relative path>:<line>\n"
        "  <body: trigger (input/state) and consequence, then the fix>\n\n"
        "P0/P1 = must fix before commit, P2 = should fix, P3 = suggestion."
    )
    return "\n\n".join(parts)


# ---------------------------------------------------------------- findings

def rel_path(root: Path, path: str) -> str:
    p = Path(path)
    if p.is_absolute():
        # lexical only: resolving would turn a changed symlink into its target's path
        for r in (root, root.resolve()):
            try:
                return str(Path(os.path.normpath(p)).relative_to(r))
            except ValueError:
                continue
        return path
    return path


def parse_findings(root: Path, text: str) -> list[dict]:
    findings: list[dict] = []
    current: dict | None = None
    for line in text.splitlines():
        m = FINDING_RE.match(line)
        m2 = None if m else FINDING_NOLOC_RE.match(line)
        if m or m2:
            if current:
                findings.append(current)
            prio = (m or m2).group(1)
            current = {
                "severity": SEVERITY[prio],
                "priority": prio,
                "title": (m or m2).group(2).strip(" *"),
                "path": rel_path(root, m.group(3)) if m else None,
                "line": int(m.group(4)) if m and m.group(4) else None,
                "body": [],
            }
        elif current is not None:
            current["body"].append(line)
    if current:
        findings.append(current)
    for f in findings:
        f["body"] = "\n".join(l.strip() for l in f["body"]).strip()
    return findings


def in_scope(finding: dict, files: list[str] | None) -> bool:
    if not files or not finding.get("path"):
        return True
    return finding["path"] in files


def render_finding(fid: str, f: dict) -> str:
    loc = f"`{f['path']}:{f['line']}`" if f.get("path") and f.get("line") else (
        f"`{f['path']}`" if f.get("path") else "—")
    prio = f" ({f['priority']})" if f.get("priority") else ""
    return (f"### {fid} — {f['title']}\n\n"
            f"**File:** {loc}\n"
            f"**Severity:** {f['severity']}{prio}\n"
            f"**Issue:** {f['body'] or '(no detail given)'}\n")


def review_path(root: Path, session: str | None) -> Path:
    """REVIEW.md, unless it belongs to another session — then REVIEW-<id8>.md (never overwrite)."""
    default = root / "REVIEW.md"
    if not default.exists():
        return default
    m = re.search(r"^session: *(\S+)", default.read_text(errors="ignore"), re.M)
    if session and m and m.group(1) == session:
        return default
    # unknown owner (no session: line, or our own id unresolved) counts as someone else's
    owner = m.group(1)[:8] if m else "unknown"
    alt = root / f"REVIEW-{(session or dt.datetime.now().strftime('%H%M%S'))[:8]}.md"
    log(f"REVIEW.md belongs to session {owner}; writing {alt.name} instead")
    return alt


def write_review(root: Path, out: Path, *, status: str, files: list[str],
                 sections: list[tuple[str, list[dict], str]], thread_id: str | None,
                 secret_status: str, engine: str = "codex", session: str | None = None,
                 base: str | None = None) -> dict:
    counts = {s: 0 for s in ORDER}
    for _, items, _ in sections:
        for f in items:
            counts[f["severity"]] += 1
    total = sum(counts.values())
    head = git(root, "rev-parse", "HEAD").strip() or "(no commits)"
    fm = ["---",
          f"reviewed: {dt.datetime.now().astimezone().isoformat(timespec='seconds')}",
          f"base: {base or 'HEAD'}",
          f"head: {head} + uncommitted",
          f"session: {session or 'null'}",
          "files_reviewed_list:" if files else "files_reviewed_list: []"]
    fm += [f"  - {f}" for f in files]
    fm += ["findings:"] + [f"  {s.lower()}: {counts[s]}" for s in ORDER] + [f"  total: {total}"]
    fm += [f"status: {status}", f"engine: {engine}",
           f"codex_thread: {thread_id or 'null'}", f"secret_scan: {secret_status}", "---", ""]
    body = ["# Code Review", ""]
    rng = f"`{base or 'HEAD'}..working tree`"
    if status == "skipped":
        body.append("**Status:** skipped — no changes in scope.")
    elif status == "clean":
        body += [f"**Status:** clean — {len(files)} files reviewed, no findings.", "",
                 f"**Diff range:** {rng}", f"**Secret scan:** {secret_status}"]
    else:
        note = (" A review round did not complete, so this review is incomplete."
                if status == "incomplete" else "")
        body += [f"**Status:** {status} — {total} findings ({counts['Critical']} critical, "
                 f"{counts['Warning']} warning, {counts['Suggestion']} suggestion, {counts['Nit']} nit).{note}",
                 "", f"**Files reviewed:** {len(files)}", f"**Diff range:** {rng}",
                 f"**Secret scan:** {secret_status}"]
    seq = {s: 0 for s in ORDER}
    for heading, items, raw in sections:
        if status == "skipped":
            break
        body += ["", f"## {heading}", ""]
        if not items:
            body.append(raw.strip() if raw.strip() else "_No findings._")
            continue
        for f in sorted(items, key=lambda x: ORDER.index(x["severity"])):
            seq[f["severity"]] += 1
            body.append(render_finding(f"{PREFIX[f['severity']]}-{seq[f['severity']]:02d}", f))
    out.write_text("\n".join(fm) + "\n".join(body).rstrip() + "\n")
    ensure_ignored(root, out.name)
    return counts


def ensure_ignored(root: Path, name: str) -> None:
    if run(["git", "check-ignore", "-q", name], cwd=root).returncode == 0:
        return
    gi = root / ".gitignore"
    existing = gi.read_text() if gi.exists() else ""
    sep = "" if not existing or existing.endswith("\n") else "\n"
    gi.write_text(existing + sep + "REVIEW*.md\n")


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--files", nargs="+", metavar="PATH",
                    help="limit the review to these repo-relative files (multi-session dirty tree)")
    ap.add_argument("--from-text", nargs=2, metavar=("ROUND1", "ROUND2"),
                    help="agent fallback: build REVIEW.md from two text files in the "
                         "`- [P0-P3] title — path:line` format instead of calling Codex")
    ap.add_argument("--print-prompt", action="store_true",
                    help="print the round-2 checklist prompt and exit (for the agent fallback)")
    ap.add_argument("--base", metavar="REF",
                    help="also review commits since REF (session work that is already committed)")
    args = ap.parse_args()

    top = run(["git", "rev-parse", "--show-toplevel"])
    if top.returncode != 0:
        log("not inside a git repository")
        return 2
    root = Path(top.stdout.strip())

    base = args.base
    if base and run(["git", "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}"],
                    cwd=root).returncode != 0:
        log(f"--base {base} is not a valid commit")
        return 2
    changed = changed_files(root, base)
    if args.files:
        # abspath, not resolve(): a changed symlink must keep its own git path
        wanted = [rel_path(root, os.path.abspath(f)) if os.path.lexists(f) else f for f in args.files]
        scope = [f for f in wanted if f in changed]
        for f in sorted(set(wanted) - set(scope)):
            log(f"not changed, ignored: {f}")
    else:
        scope = changed

    if args.print_prompt:
        print(round2_prompt(root, args.files and scope, base))
        return 0

    session, title = origin_session()
    out = review_path(root, session)

    codex, env = find_codex()
    on_codex_host = bool(os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_SESSION_ID"))
    if not args.from_text and scope and (not codex or on_codex_host):
        reason = "running on a Codex host" if on_codex_host else "codex not found"
        print(f"FALLBACK: {reason} — use the agent fallback in SKILL.md "
              f"(then rerun with --from-text ROUND1 ROUND2).")
        return 3

    if not scope:
        write_review(root, out, status="skipped", files=[], sections=[], thread_id=None,
                     secret_status="skipped", engine="agent" if args.from_text else "codex",
                     session=session, base=base)
        print(f"Skipped — no changes in scope. See {out.name}.")
        return 0

    secret_status, leaks = secret_scan(root, scope, base)
    limit = scope if args.files else None
    thread_id = None
    round2_ok = True
    if limit:
        # --uncommitted / --base refuse a custom prompt, so a scoped review is prompt-only.
        # It is a scope note, not a checklist: round 1 stays free of the commons.
        diff = f"`git diff {base}` (commits since {base} plus uncommitted) and untracked files" if base else \
            "`git diff --cached` (staged, what will be committed), `git diff` (unstaged) and " \
            "untracked files"
        r1_args = ["review", f"Review the changes in {diff}, but ONLY in these files; other "
                   "changed files belong to another session:\n" + "\n".join(f"- {f}" for f in limit)]
    else:
        r1_args = ["review", "--base", base] if base else ["review", "--uncommitted"]

    if args.from_text:
        engine = "agent"
        r1_text = Path(args.from_text[0]).read_text()
        r2_text = Path(args.from_text[1]).read_text()
        for label, text in (("round 1", r1_text), ("round 2", r2_text)):
            if not text.strip() or text.lstrip().startswith("_"):
                log(f"{label} file is empty or a failure note; the review is incomplete")
                round2_ok = False
    else:
        engine = "codex"
        try:
            thread_id, r1_text = codex_exec(codex, env, root, r1_args)
        except Exception as exc:  # noqa: BLE001
            log(str(exc))
            print("FALLBACK: codex review failed — use the agent fallback in SKILL.md.")
            return 3
        if thread_id:
            name_thread(thread_id, session, title, env)
            try:
                _, r2_text = codex_exec(codex, env, root,
                                        ["resume", thread_id, round2_prompt(root, limit, base)])
            except Exception as exc:  # noqa: BLE001
                log(str(exc))
                r2_text, round2_ok = f"_Checklist round failed: {exc}_", False
        else:
            log("no thread_id in codex output; checklist round skipped")
            r2_text, round2_ok = "_Checklist round skipped: Codex returned no thread id._", False

    def key(f: dict) -> tuple:
        return (f.get("path"), f.get("line"), re.sub(r"\W+", " ", f["title"].lower()).strip())

    r1 = [f for f in parse_findings(root, r1_text) if in_scope(f, limit)]
    seen = {key(f) for f in r1 if f.get("path")}
    # drop only exact repeats (same place, same issue); unlocated findings are always kept
    r2 = [f for f in parse_findings(root, r2_text)
          if in_scope(f, limit) and (not f.get("path") or key(f) not in seen)]
    # Unparsed text is shown verbatim only when nothing parsed (e.g. "No findings." or an error note)
    raw1 = "" if parse_findings(root, r1_text) else r1_text
    raw2 = "" if parse_findings(root, r2_text) else r2_text

    # Raw text that parsed to nothing counts as clean only if it says so; otherwise the
    # findings are sitting unparsed in REVIEW.md and "clean" would be a lie.
    unparsed = [raw for raw in (raw1, raw2)
                if raw.strip() and not NO_FINDINGS_RE.search(raw) and not raw.lstrip().startswith("_")]

    sections = []
    if leaks:
        sections.append(("Secret scan", leaks, ""))
    sections += [("General findings", r1, raw1), ("Checklist findings", r2, raw2)]
    if not round2_ok or secret_status == "error":
        status = "incomplete"
    else:
        status = "issues_found" if (leaks or r1 or r2 or unparsed) else "clean"
    counts = write_review(root, out, status=status, files=scope, sections=sections,
                          thread_id=thread_id, secret_status=secret_status, engine=engine,
                          session=session, base=base)
    total = sum(counts.values())
    if status == "clean":
        print(f"Clean — {len(scope)} files reviewed, no findings ({engine}, secret_scan: "
              f"{secret_status}). See {out.name}.")
    else:
        extra = " + unparsed review text" if unparsed else ""
        extra += "; a review round did not complete (incomplete)" if status == "incomplete" else ""
        print(f"Found {total} findings ({counts['Critical']} critical, {counts['Warning']} warning, "
              f"{counts['Suggestion']} suggestion, {counts['Nit']} nit{extra}; {engine}, secret_scan: "
              f"{secret_status}). See {out.name}.")
    return 4 if status == "incomplete" else 0


if __name__ == "__main__":
    sys.exit(main())
