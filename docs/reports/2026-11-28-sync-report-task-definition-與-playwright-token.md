---
session: 2026-11-27-商品搜尋統一 (4603a81d-65b1-48e7-a190-8e7320fac08c)
---

# improve：sync-report 跳過 Task Definition、headless-shots 不在 Playwright 帶 token

# Description

商品搜尋統一（sparktoy）wrap-up 時發現的兩個摩擦。

# Changes Made

- **`bin/notion-io.py` sync-report**：報告開頭是 fetch-task 管理的 `# Task Definition` 區塊（對應任務的「說明」欄位，不在頁面內文）時，「跳過任務上已有的開頭章節」第一節就對不上，整份連 `# Context` 一起附加，Notion 任務多出第二份 Context 要手刪。改成先拿掉 `<!-- fetch-task:definition:start -->…end -->` 區塊再比對。
- **`skills/headless-shots/SKILL.md`**：登入 token 只放 shell 變數直接傳給腳本；不要放進 Playwright MCP `browser_run_code_unsafe`（`code` 或 `filename` 都會把整段程式碼連 token 印回 transcript，同一 session 發生兩次）。

# Verification

- 用該報告實跑新的前處理：`h1_sections` 第一節變成 `Context`（原本是 `Task Definition`），可被跳過；`python3 -m py_compile bin/notion-io.py` 通過。
- 沒有對 Notion 重跑整個 sync（該任務已手動清掉重複的 Context）。

# Result

- 下次從 fetch-task 任務檔產生的報告同步時，不會再附加第二份 `# Context`。
