#!/bin/sh
# SessionStart(compact) hook: print files THIS session (and its subagents) wrote that are still
# uncommitted, grouped by git repo — so a compaction summary can't erase who owns what.
# stdin: hook JSON with transcript_path. stdout is injected into the model's context.
exec python3 -c '
import json, os, re, subprocess, sys, glob
try:
    hook = json.load(sys.stdin)
except Exception:
    sys.exit(0)
tp = hook.get("transcript_path") or ""
if not os.path.isfile(tp):
    sys.exit(0)
files = [tp] + glob.glob(os.path.join(tp[:-6], "subagents", "*.jsonl"))
WRITE_BASH = re.compile(r"write_text|open\([^)]*[\x27\x22]w|\.write\(|sed -i|cat >|tee |cp |mv |> *[\x27\x22]?/")
ABS = re.compile(r"(/(?:Users|home|private/tmp)/[^\s\x27\x22`;|&<>(){}]+)")
paths = set()
for f in files:
    try:
        fh = open(f, encoding="utf-8")
    except OSError:
        continue
    for line in fh:
        if "tool_use" not in line:
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        for b in (d.get("message") or {}).get("content") or []:
            if not isinstance(b, dict) or b.get("type") != "tool_use":
                continue
            inp = b.get("input") or {}
            name = b.get("name")
            if name in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
                p = inp.get("file_path") or inp.get("notebook_path")
                if p:
                    paths.add(p)
            elif name == "Bash":
                cmd = inp.get("command") or ""
                if WRITE_BASH.search(cmd):
                    paths.update(m.rstrip(".,:") for m in ABS.findall(cmd))
repos = {}
for p in paths:
    d = p if os.path.isdir(p) else os.path.dirname(p)
    if not os.path.isdir(d):
        continue
    r = subprocess.run(["git", "-C", d, "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if r.returncode == 0:
        repos.setdefault(r.stdout.strip(), set()).add(os.path.realpath(p))
out = []
for repo, mine in sorted(repos.items()):
    st = subprocess.run(["git", "-C", repo, "-c", "core.quotepath=false", "status", "--porcelain"],
                        capture_output=True, text=True).stdout.splitlines()
    hits = []
    for l in st:
        rel = l[3:].split(" -> ")[-1].strip().strip("\x22")
        full = os.path.realpath(os.path.join(repo, rel))
        if full in mine or any(m.startswith(full.rstrip("/") + "/") for m in mine):
            hits.append(l)
    if hits:
        out.append(f"{repo}  ({len(hits)} uncommitted)")
        out += ["  " + h for h in hits]
if out:
    print("[uncommitted-by-session] Files THIS session wrote that are still uncommitted (from the transcript, not the summary). "
          "A listed file can still carry another session\x27s hunks, and unlisted dirty files are not this session\x27s; confirm with find-session --touched before attributing or committing:")
    print("\n".join(out))
'
