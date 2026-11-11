---
session: 2026-11-11-業務報價單-1104回饋 (ea0899f6-154b-41c6-a938-46f179b3be3f)
---

# improve：create-tasks／sync-report 的 Notion 寫入

## 摘要

| 技能 | 問題（sparktoy 業務報價單 session，2026-11-11） | 改法 |
|---|---|---|
| create-tasks | 建票 agent 寫 `<mention-page …/>` 存成純文字；LINE 原文裡的 `-----`、`1.` 被轉成分隔線與清單 | §9.1 加「Notion markup」一段：頁面連結用 `<mention url="…"/>`；聊天／LINE 摘錄放 code block |
| sync-report | 任務頁建立時已有 `# Unsolved Issues`，報告又附上自己的一段 → B2、B5 兩頁各有兩段，事後手動刪 | step 8：目標已有 `# Unsolved Issues` 時，用報告那段取代（同一個 `update_content` 多一個 op 刪舊段，先確認舊項目已解或已帶過去），不留兩段 |

# Changes Made

- `skills/create-tasks/SKILL.md`：§9.1 body 範本後加一段 Notion markup 規則。
- `skills/sync-report/SKILL.md`：step 8 加「既有 `# Unsolved Issues` 由報告版取代」。

# Result

下次 create-tasks 建票、sync-report 回寫時，連結會正確顯示、聊天原文不變形、Unsolved Issues 不重複。未在新 session 實跑驗證。
