---
session: 2026-11-26-後端-首頁作品列表與缺口提案spec (fb406e41-4e24-46b9-b984-183ee9fc7ba9)
---

# improve：交接檔用 session 名稱，`[ref]` 只當參考

# Description

- sontis-ai 的交接檔請接手方開工前 SendMessage 給 `2026-11-26-ui-library對齊定案 [64b94a]`。對方 session 重啟後 ref 變成 `[6412dc]`，帶舊 ref 的第一次回報送不到（`No agent named … is reachable`），要先 `ListAgents` 再用名稱重送。

# Changes Made

- `docs/agents-and-sessions.md`「Claude 開新 session 時就命名」那條：交接檔只填名稱；SendMessage 用名稱本身，`[ref]` 只當參考、重啟會變，送失敗先 `ListAgents` 再用名稱重送。

# Result

- 只改這一句；同檔其他 session 未 commit 的改動沒有一起 commit。
