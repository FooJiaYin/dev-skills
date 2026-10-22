---
session: 2026-10-22-龍杰測試回報 (969c9ea5-059e-4df6-ba91-1cb5d5428ea1)
---

# improve：sync-report 錨點、headless-shots 啟動等待

# Description

- 來源：sparktoy 龍杰 10/22 測試回報 wrap-up 中遇到的兩個摩擦。

# Changes Made

- `skills/sync-report/SKILL.md`：`update_content` 錨點說明——Notion 把行內程式碼存成 `<code>…</code>`（粗體 `<b>`），含反引號的 `old_str` 永遠比對不到（實際三次 `No matches found`）；改用純文字片段或從 `notion-fetch` 複製位元組。
- `skills/headless-shots/scripts/shoot.mjs`、`drive-example.mjs`：等 Chrome 遠端除錯埠從 40×250ms（10 秒）改為 120×250ms（30 秒）。實際 Chrome 啟動超過 10 秒，腳本以 `ECONNREFUSED` 失敗。

# Result

- 兩處各一行，無行為以外的變更。另一項（worktree 的 node_modules 用 `cp -cR` 而非 symlink）存在 sparktoy 專案記憶，未改 skill。
