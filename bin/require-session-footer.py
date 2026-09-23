#!/usr/bin/env python3
"""PreToolUse(Bash) hook: deny `git commit` whose message lacks a `Session: <name> (<id>)` footer.
Reads hook JSON from stdin; prints a deny decision with the current session name/id so the
agent can add the footer and retry. Exit 0 always (never blocks on its own errors)."""
import json, os, re, sys, glob

def main():
    try:
        hook = json.load(sys.stdin)
    except Exception:
        return
    if hook.get("tool_name") != "Bash":
        return
    cmd = (hook.get("tool_input") or {}).get("command") or ""
    # `git` must be the command word of a segment and `commit` its subcommand — a grep/echo
    # whose *text* mentions git…commit is not a commit (it used to be denied, and subagents
    # read the deny message as a prompt injection).
    hit = re.search(r"(?:^|[\n;&|(])\s*(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)*git"
                    r"(?:\s+(?:-C|-c|--git-dir|--work-tree)(?:=|\s+)\S+)*\s+commit\b", cmd)
    if not hit:
        return
    # Message reused from an existing commit → nothing to add here. Look only AFTER `commit`:
    # `git -C <repo> commit` carries a -C that is a path, not a reuse-message flag.
    if re.search(r"--no-edit|--reuse-message|--reedit-message|\s-[cC]\s|--fixup|--squash",
                 cmd[hit.end():]):
        return
    text = cmd
    m = re.search(r"(?:-F|--file)[=\s]+([^\s;&|]+)", cmd)
    if m and m.group(1) != "-":
        try:
            text += open(os.path.expanduser(m.group(1)), encoding="utf-8").read()
        except OSError:
            pass
    if "Session:" in text:
        return
    sid = hook.get("session_id") or os.environ.get("CLAUDE_CODE_SESSION_ID") or "?"
    name = None
    tp = hook.get("transcript_path") or ""
    if not os.path.isfile(tp):
        cwd = hook.get("cwd") or os.getcwd()
        enc = re.sub(r"[^A-Za-z0-9]", "-", cwd)
        cands = glob.glob(os.path.expanduser(f"~/.claude/projects/{enc}/{sid}.jsonl"))
        tp = cands[0] if cands else ""
    # Latest customTitle wins: the log's line 1 keeps the title from when the log was created,
    # so after a rename-session it is stale.
    if os.path.isfile(tp):
        try:
            for line in open(tp, encoding="utf-8"):
                if "customTitle" in line:
                    try:
                        name = json.loads(line).get("customTitle") or name
                    except ValueError:
                        pass
        except OSError:
            pass
    # Fallback — session log (dev-skills/bin/session-log.py) line 1: "# <title> · session <id> · …"
    lp = tp[:-6] + ".log.md" if tp.endswith(".jsonl") else ""
    if name is None and lp and os.path.isfile(lp):
        try:
            head = open(lp, encoding="utf-8").readline().strip().lstrip("# ")
            t = head.split(" · ")[0]
            if t and t != "(untitled)":
                name = t
        except OSError:
            pass
    name = name or "<report/branch title>"
    reason = (f"Commit message is missing the mandatory footer. Add this line before Co-Authored-By and retry:\n"
              f"Session: {name} ({sid})")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                             "permissionDecision": "deny",
                                             "permissionDecisionReason": reason}}))

if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
