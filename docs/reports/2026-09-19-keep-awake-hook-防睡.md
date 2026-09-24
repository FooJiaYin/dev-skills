---
session: 2026-09-19-keep-awake-hook-防睡 (daa857f1-31d7-43b3-90da-062af551a2b9)
---

# keep-awake hook：Remote Control 防睡＋不再誤殺 caffeinate

```
現在 ❌                                   改後 ✓
────────────────────────────────         ──────────────────────────────────────
切到 Remote → 3 分鐘後 Mac 睡 → 斷線        Remote 下送訊息 → hook 開 caffeinate -i -w <claude pid>
CLAUDE.md 叫 agent 自己開/kill caffeinate   派 agent → hook 開 caffeinate -i -t 7200（自己的 pidfile）
agent 收尾 pkill caffeinate → 殺掉使用者的   CLAUDE.md：禁止自己開/kill，絕不 pkill/killall
```

# Description

- 使用者切到 Remote Control 時 Mac 一直休眠斷線，且其他 agent 會擅自停掉使用者手動開的 caffeinate。
- 診斷：`pmset` 顯示電池模式 `displaysleep 2`、`sleep 1`，Claude Code 本身不持有防睡 assertion。
- 誤殺根因：8/27 sparktoy session 的 `/improve` 在全域 CLAUDE.md 加了「派 agent 前 `caffeinate -i -t 7200 &`，整輪結束時 `kill`」；過去 5 個 session 用 `pkill -x caffeinate` / `pkill -f 'caffeinate -i'` 收尾。
- 使用者：「把它寫成hook不好嗎」→ 改用 hook，由 harness 執行，不靠 agent 判斷。

# Changes Made

- 新增 hook 腳本 `bin/keep-awake.py`
  - `agent` 模式（PreToolUse `Agent|Task|Workflow`）：關掉自己 pidfile 裡的舊 caffeinate，重開 `caffeinate -i -t 7200`。
  - `remote` 模式（UserPromptSubmit）：有 `$CLAUDE_CODE_BRIDGE_SESSION_ID` 且尚未開過才開 `caffeinate -i -w <claude pid>`；claude pid 由 process tree 往上找 comm 為 `claude` 的 process。
  - pidfile `/tmp/claude-keepawake-<session_id>-<mode>.pid`；kill 前確認該 pid 真的是 caffeinate；任何錯誤都 exit 0。
- `~/.claude/settings.json`（不在 git）：加上述兩個 hook。
- `~/.claude/CLAUDE.md`（不在 git）：Background agents #1 改為「防睡由 hook 處理，不要自己開或 kill caffeinate，絕不 `pkill`／`killall caffeinate`」。

決策：用 `-i` 不用 `-d`（只需網路不斷，螢幕可關，省電）；agent 模式維持 2 小時上限，不綁 claude 存活（否則派過一次 agent 整個 session 都不睡）。

# Result

- 本機測試：連續兩次 `agent` → 舊 caffeinate 被關、新的 `caffeinate -i -t 7200` 起來；無 bridge 變數 `remote` → 不開；手動設變數 `remote` → `caffeinate -i -w 46548`（46548 = claude 本身），重複觸發不多開。`settings.json` JSON 驗證通過。
- 限制：Remote 下第一則訊息送出前不會觸發；闔蓋仍會睡（macOS 限制）。

# Unsolved Issues

- [Warning] `bin/keep-awake.py` — 真正連上 Remote Control 時 hook 環境是否帶 `CLAUDE_CODE_BRIDGE_SESSION_ID` 未實測（deferred because: 本 session 未連 Remote）。驗法：Remote 送一則訊息後在 Mac 跑 `pgrep -fl 'caffeinate -i -w'`。
- [Suggestion] 已開著的 session 需重開才會套用新 hook。

# References

- https://code.claude.com/docs/en/remote-control.md
- https://code.claude.com/docs/en/hooks.md
- https://code.claude.com/docs/en/env-vars.md
