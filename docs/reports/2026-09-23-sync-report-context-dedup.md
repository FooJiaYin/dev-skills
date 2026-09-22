---
title: sync-report 首次同步 Context 去重
session: sync-report 首次同步 Context 去重 (01a0cabb-0def-7271-af60-9ede20cbdcf0)
---

# Description

- 修正由 `/fetch-task` 衍生的報告首次同步回同一張 Notion 任務時，重複附加既有 `# Context` 的問題。

# Changes Made

- `sync-report` 在附加本文前比對 Notion 與報告的前導頂層區段。
- 完全相同的前導區段視為既有內容，只附加剩餘報告；比對不明確時停止並詢問，避免誤刪或重複。
- 更新 verbatim hard constraint，明列唯一可省略的是目標已存在的相同前導區段。

# Verification

- `quick_validate.py skills/sync-report`：通過，`Skill is valid!`。
- 實際清理本次 Notion 任務後回讀：`# Context`、`# Changes Made`、`# Updates` 各一份，兩個來源附件仍保留，review 修正區段仍存在。

# Result

- 首次同步 fetched-task report 時不再重複建立 `# Context`；再次同步的既有 delta-only 規則不變。
