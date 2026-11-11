---
session: 2026-11-11-文字匯入-訊息日期帶入發單日 (2c03987c-2218-467c-8820-60f4945680fe)
---

# fetch-task：手建任務缺 `# Context` 標題時的處理

# Description

- 在 sparktoy 專案裡沒走 `/create-tasks`，直接用 `notion-create-pages` 建了一張任務，內文以 `# Context` 開頭；Notion 建立時把開頭的 H1 當成重複標題拿掉，任務只剩「來源：<mention>…」等內容。
- `/fetch-task` 遇到沒有 `# Context` 的任務會寫佔位文字，這種情況會把真正的會議摘錄丟到佔位文字之外，之後 `/sync-report` 也對不上 `# Context`。

# Changes Made

- `skills/fetch-task/SKILL.md`：佔位規則加例外——內文以會議摘錄開頭（手建任務標題被吃掉）時，把內容放進本機 `# Context`，並提醒使用者在 Notion 開頭補回標題（`insert_content` start）。建立端照 `/create-tasks` 的做法在開頭留空行即可避免。

# Result

- 手建任務下次 `/fetch-task` 不會再把會議摘錄當成「沒有 Context」。`/fetch-task` 仍維持不寫 Notion。
