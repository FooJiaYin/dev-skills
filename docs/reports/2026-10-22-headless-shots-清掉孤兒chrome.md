---
session: 2026-10-22-新增利潤率參數並套用露天與國內批發公式-98d6cc (be82cda7-bc82-4959-a49f-17ca6d416e61)
---

# headless-shots：node 被殺時也要帶走 Chrome

# Description

- 使用者點 Chrome 打不開。原因：多個 session 的 headless-shots 腳本被 tool timeout 殺掉，留下孤兒 `--headless` Chrome（PPID 1）；macOS 把 Chrome 視為已在執行，點擊只喚醒那個隱形實例。
- 當下以 `open -na "Google Chrome"` 強制開出正常實例解決；孤兒程序屬其他 session，未清除。

# Changes Made

- `skills/headless-shots/scripts/shoot.mjs`、`drive-example.mjs`：spawn 後掛 `process.on("exit"|SIGINT|SIGTERM|SIGHUP)` → `chrome.kill("SIGKILL")`，任何結束路徑都帶走 Chrome（原本只在正常結束時 `chrome.kill()`）。
- `skills/headless-shots/SKILL.md` Gotchas 加一條：自寫腳本也要抄這個 hook；使用者端修法 `open -na "Google Chrome"`、清理只用 `pkill -f 'Google Chrome.*--headless'`。

# Verification

- `node --check` 兩支腳本通過。未實際跑一次截圖（本 session 無需要截圖的頁面）。

# Result

- 之後被 timeout 殺掉的截圖腳本不再留下孤兒 Chrome。
- 同次 /improve 另外寫入（不在本 repo）：`~/.claude/CLAUDE.md` Background agents 第 9 條（派實作 agent 前把 UI 要求逐字抄進 prompt 當驗收條件）；`sparktoy-erp` AGENTS.md（龍杰給的公式不可為了顯示需求自行改）。
