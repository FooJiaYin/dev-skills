---
name: cleanup-processes
description: Find and close unused servers, browsers, containers and idle Claude sessions on this Mac, starting from whatever is running right now (no fixed list of suspects). Use when the user says "很慢", "電腦很卡", "關掉不用的", "砍掉不必要的 process", "關掉閒置的 session", "清 server"; when agents or tests run much slower than usual; before starting a dev server / tests / screenshots / a new session on an already-strained machine; when a port is held by an unknown process; and during /wrap-up cleanup to close the servers, browsers and containers this session started.
---

Runs on: macOS + Claude Code. Codex: the process and port sections work, but only Claude Code sessions are listed (resume with the host's own command). Other OS: the script exits with a note — look at memory, top processes and listening ports with that system's own tools, then apply the same signals and tiers; use your judgment.

# cleanup-processes

## 1. Look first
`/usr/bin/python3 <this skill>/scripts/check.py` (read-only; `--json` for data). It prints swap/load, top memory users grouped by kind, Claude sessions, listening ports, colima/docker, and a suggested close / ask / keep split. Decide from the table; the split is a suggestion.
If it prints the "探測失敗" warning, an empty table does not mean there is nothing to close.

## 2. Signals that something is unused (not by name)
- Orphan: the process or session that started it is gone.
- Started with headless / automation flags (`--headless`, `--remote-debugging-port`, a temp `--user-data-dir`, playwright).
- Open for a long time and listening on a port.
- Many of the same kind.
- Reserved far more than it uses (VM reserves 8 GB, containers use a few hundred MB).

## 3. Three tiers
- **Close directly** (then list what you closed and how to get it back): Claude sessions `idle` for over 1 h — first look at the listening child processes the script lists for it, they die with the session; orphan browsers with automation flags, only once nothing alive is connected to their debugging port.
- **List and ask the user**: every orphan server (nothing proves who started it — it may be a demo left up on purpose); sessions `waiting` (waiting for the user) or idle under 1 h; automated browsers whose debugging port is in use or can't be checked; Docker / colima VM (tests need it restarted); browser-automation MCP daemons; anything whose owner is unclear.
- **Never touch**: `busy` / `shell` sessions; this session and its parent chain; databases (postgres, …); port forwarders (ssh, limactl, docker-proxy, com.docker.* — may be a DB inside a container); the user's own browser windows (not headless); `caffeinate` (**never `pkill` / `killall caffeinate`**); system processes.

## 4. Closing and getting it back
- Re-read the status right before closing (it may have just changed). Always by pid — never `pkill -f` / name-wide kills.
- Session: `kill -TERM <pid>`; resume with `claude --resume <sessionId>` (VS Code: reopen the tab).
- Server / browser: `kill -TERM <pid>` (the browser's root pid); after a few seconds `kill -0 <pid>`, and only if it is still there `kill -KILL <pid>`. Never by name.
- colima: `colima stop`; to lower its cap, `colima start --memory <GB>`.
- If the permission mode blocks a `kill` (auto mode does), don't retry with another spelling: give the user the exact line to run (`! kill <pids>`) or ask them to switch to default mode. (Seen: three orphan servers stayed up because the kill was denied.)
- Confirm before reporting "closed": `kill -0 <pid>` fails, `lsof -i :<port>` is empty.
- Measure swap again and report a before / after table.

## 5. Pitfalls
- `ps` RSS hides compressed memory (a VM showed 270 MB but held 8 GB + 14 GB compressed) — read `top`'s MEM + CMPRS.
- Claude session pid, name and status are in `~/.claude/sessions/<pid>.json` — don't guess which process is which session.
