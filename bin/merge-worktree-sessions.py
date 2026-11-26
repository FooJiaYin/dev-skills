#!/usr/bin/env python3
"""Merge Claude Code session data from <repo>/.claude/worktrees/* project dirs back into the repo's main project dir.

Since ~2.1.331, EnterWorktree stores the transcript under the worktree's project dir, so the session
disappears from the main project's session list. This moves it back: new files are moved, continuations
of a session already in main are appended (deduped by uuid), duplicate .log.md are appended, state files
keep main's copy. gitBranch / worktree-state stay intact, so the UI still shows which worktree was used.
Backs up main + worktree dirs + history.jsonl to ~/.claude/projects-backup-<ts> before writing.
Don't run while a session in those dirs is live (pass --skip <session-id> for it).

Usage: merge-worktree-sessions.py <repo-root> [--apply] [--skip <id>]... [--rewrite-cwd]
  dry-run by default; --rewrite-cwd also rewrites "cwd" to the repo root (not needed for resume).
"""
import json, os, re, shutil, sys, glob, time

args = sys.argv[1:]
APPLY = "--apply" in args
REWRITE_CWD = "--rewrite-cwd" in args
SKIP_SESSIONS = {args[i + 1] for i, a in enumerate(args) if a == "--skip" and i + 1 < len(args)}
pos = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] != "--skip")]
ROOT = os.path.abspath(pos[0] if pos else os.getcwd()).rstrip("/")
PROJ = os.path.expanduser("~/.claude/projects")
MAIN = f"{PROJ}/" + re.sub(r"[^A-Za-z0-9]", "-", ROOT)
PREFIX = MAIN + "--claude-worktrees-"
BACKUP = os.path.expanduser(f"~/.claude/projects-backup-{time.strftime('%Y%m%d-%H%M%S')}")

CWD_RE = re.compile(r'"cwd":"' + re.escape(ROOT) + r'/\.claude/worktrees/[^/"]+')

def rewrite(line):
    return CWD_RE.sub('"cwd":"' + ROOT, line) if REWRITE_CWD else line

def act(msg, fn=None):
    print(("APPLY " if APPLY else "DRY   ") + msg)
    if APPLY and fn:
        fn()

def merge_tree(src, dst):
    for dirpath, _, files in os.walk(src):
        rel = os.path.relpath(dirpath, src)
        for f in files:
            s = os.path.join(dirpath, f); d = os.path.join(dst, rel, f)
            if os.path.exists(d):
                print(f"      keep main copy of {os.path.relpath(d, MAIN)} (dup in worktree)")
            else:
                os.makedirs(os.path.dirname(d), exist_ok=True); shutil.move(s, d)

wt_dirs = sorted(glob.glob(PREFIX + "*"))
if APPLY:
    os.makedirs(BACKUP)
    shutil.copytree(MAIN, f"{BACKUP}/{os.path.basename(MAIN)}")
    for d in wt_dirs:
        shutil.copytree(d, f"{BACKUP}/{os.path.basename(d)}")
    shutil.copy2(os.path.expanduser("~/.claude/history.jsonl"), f"{BACKUP}/history.jsonl")
    print("backup:", BACKUP)

moved_projects = set()
for wd in wt_dirs:
    name = wd[len(PREFIX):]
    print(f"\n== {name}")
    all_moved = True
    for e in sorted(os.listdir(wd)):
        src = f"{wd}/{e}"; dst = f"{MAIN}/{e}"
        sid = e.split(".")[0]
        if sid in SKIP_SESSIONS:
            print(f"SKIP  {e} (live session)"); all_moved = False; continue
        if e == ".tree-cache.json":
            act(f"drop {e}", lambda: os.remove(src)); continue
        if e.endswith(".jsonl"):
            if not os.path.exists(dst):
                def mv(src=src, dst=dst):
                    st = os.stat(src)
                    with open(src) as f: lines = [rewrite(l) for l in f]
                    with open(dst, "w") as f: f.writelines(lines)
                    os.utime(dst, (st.st_atime, st.st_mtime)); os.remove(src)
                act(f"move {e}" + (" (rewrite cwd)" if REWRITE_CWD else ""), mv)
            else:
                def app(src=src, dst=dst):
                    st = os.stat(src)
                    with open(dst) as f: have = {json.loads(l).get("uuid") for l in f if l.strip().startswith("{")} - {None}
                    with open(src) as f: lines = [l for l in f]
                    add = []
                    for l in lines:
                        try: u = json.loads(l).get("uuid")
                        except Exception: u = None
                        if u is None or u not in have: add.append(rewrite(l))
                    with open(dst, "a") as f: f.writelines(add)
                    os.utime(dst, (st.st_atime, st.st_mtime)); os.remove(src)
                act(f"append {e} -> main copy (continuation)", app)
        elif os.path.isdir(src):
            if not os.path.exists(dst): act(f"move dir {e}/", lambda src=src, dst=dst: shutil.move(src, dst))
            else: act(f"merge dir {e}/", lambda src=src, dst=dst: (merge_tree(src, dst), shutil.rmtree(src)))
        elif e.endswith(".log.md"):
            if not os.path.exists(dst): act(f"move {e}", lambda src=src, dst=dst: shutil.move(src, dst))
            else:
                def appmd(src=src, dst=dst, name=name):
                    with open(src) as f: body = f.read()
                    with open(dst, "a") as f: f.write(f"\n\n<!-- merged from worktree {name} log -->\n" + body)
                    os.remove(src)
                act(f"append {e} -> main log", appmd)
        else:  # log.state.json, reprint.md
            if not os.path.exists(dst): act(f"move {e}", lambda src=src, dst=dst: shutil.move(src, dst))
            else: act(f"drop {e} (main copy kept)", lambda src=src: os.remove(src))
    if all_moved:
        act(f"rmdir {os.path.basename(wd)}", lambda wd=wd: os.rmdir(wd))
    moved_projects.add(name)

# history.jsonl: point worktree projects at main
H = os.path.expanduser("~/.claude/history.jsonl")
pat = re.compile(r'"project":"' + re.escape(ROOT) + r'/\.claude/worktrees/[^"]+"')
with open(H) as f: lines = f.readlines()
n = sum(1 for l in lines if pat.search(l))
def fixh():
    with open(H, "w") as f: f.writelines(pat.sub('"project":"' + ROOT + '"', l) for l in lines)
act(f"history.jsonl: repoint {n} entries to main", fixh)
