---
title: improve：sync-report 的 Notion token 備案、wrap-up 收回 scratchpad 成果
date: 2026-10-24
session: 2026-10-23-官網V1改版 (37de2c34-8782-4f7e-8bba-a15c85e3ce1c)
---

# 摘要

| Skill | 改了什麼 | 觸發的摩擦 |
|---|---|---|
| `sync-report` | Roadmap 回 404 時，除了請使用者重連 MCP，若 repo 或上層有 `.env` 的 `NOTION_TOKEN`，提供「用 integration token 直接打 API」的備案 | Notion MCP 登入的是 DropOut workspace，meetmeoffline 的 Roadmap 404，同步只能跳過；這個專案其實有 `NOTION_TOKEN` 可用 |
| `wrap-up`（full.md 第 6 步） | Move 分類加上「掃 session scratchpad」：可重用的腳本、驗收清單、已發布報告的原始檔搬進 `scripts/`、`docs/`，並拿掉寫死的 scratchpad 路徑 | 驗收清單與 QA 腳本差點隨 scratchpad 消失（使用者主動提出才搬）；10/20 的 Notion 會議同步腳本已經消失 |

# 未進 skill 的部分

- `meetmeoffline/AGENTS.md` 的 `## Notion`：註明 MCP 可能登入 DropOut workspace，讀寫改用 `.env` 的 `NOTION_TOKEN`。
- 「沒有遠端就不給 push／PR 選項」：使用者選擇略過。
