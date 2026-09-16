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
    if not re.search(r"\bgit\b[^\n|;&]*\bcommit\b", cmd):
        return
    # Message reused from an existing commit → nothing to add here.
    if re.search(r"--no-edit|--reuse-message|--reedit-message|\s-[cC]\s|--fixup|--squash", cmd):
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
    # Session log (dev-skills/bin/session-log.py) line 1: "# <title> · session <id> · …"
    lp = tp[:-6] + ".log.md" if tp.endswith(".jsonl") else ""
    if lp and os.path.isfile(lp):
        try:
            head = open(lp, encoding="utf-8").readline().strip().lstrip("# ")
            t = head.split(" · ")[0]
            if t and t != "(untitled)":
                name = t
        except OSError:
            pass
    if name is None and os.path.isfile(tp):
        try:
            for line in open(tp, encoding="utf-8"):
                if "customTitle" in line:
                    try:
                        name = json.loads(line).get("customTitle") or name
                    except ValueError:
                        pass
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
