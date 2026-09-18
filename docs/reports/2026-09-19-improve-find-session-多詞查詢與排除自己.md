---
session: 2026-09-19-琢奧工作流程盤點與SOP (a169b207-bf5c-4055-ab58-232f1342198a)
---

# improve：find-session 多詞查詢與排除當前 session

# Description

- `/find-session dodo 自動化` 只命中一筆，而且就是正在執行搜尋的這個 session 自己；使用者要找的 session 裡這兩個詞不相連（「把 dodo 升級，最大化自動化…」），整句逐字比對找不到，得手動拆詞重搜。

# Changes Made

- `skills/find-session/scripts/search.py`
  - 永遠排除 `$CLAUDE_CODE_SESSION_ID`（執行搜尋的 session 一定會命中自己的查詢）。
  - 多詞 `--topic`：先整句比對；所有 scope 都沒有命中時，改為「每個詞都要出現」（AND）重搜，並印一行 `# no literal match for '…'; matched all of: a + b`。各詞的 `topic_hits` 合併。
- `skills/find-session/SKILL.md`：Topic mode 補一段說明上述行為。

Result: Success

# Result

- `--topic "dodo 自動化"`：原本 1 筆（自己）→ 現在 18 筆，前兩筆就是目標 session（390796db 與其 fork 6f6767be）。
- 單一片語仍走整句比對（`--topic "金額要從 logging"` → 1 筆，行為不變）。
- 已知雜訊（未處理）：AND 模式下，同專案的 subagent transcript（`agent-*`）只要 prompt 同時含這些詞也會列出。
