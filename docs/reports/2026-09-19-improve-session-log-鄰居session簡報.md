---
session: 2026-09-17-context-management-設計討論 (9f0295b0-6a7f-461a-8d7a-ed85f717c124)
---
# improve：resume／compact 簡報列出同專案其他 session

```
現在 ❌  resume 後只看得到本 session 的狀態
         → 使用者把「Commit／一起 push」答到隔壁同秒 resume 的 session
         → 同一題（[write] 怎麼分 hunk）在 c085e38c 和本 session 各推導一次

改後 ✓  簡報尾端多一段「同專案 24h 內其他 session」（最多 5 個）
         - be36a58b「…先-rename」09-17 19:09  ⏳ 停在未回答的問題：「三個 commit 一起 push 嗎？」
         - c085e38c「(untitled)」09-17 14:44  最後一句：「B是什麼！我不知道這個」
```

# Description

`/improve` 在 [session-log 實作](2026-09-17-session-log-working-memory-hooks.md) 那個 session 收尾時提出四項，使用者裁定：

| # | 發現 | 裁定 |
|---|---|---|
| 1 | `/report` 把 plugin 工作的 report 存到非 git 的 cwd，wrap-up 才搬 | Skip |
| 2 | hook stdout 10k 字元／Read 25k token／Bash 30k 字元上限，設計前沒查 | Memory（`reference_claude_code_output_limits`） |
| 3 | 撞到上限後直接做 6 段 hook 拆印，被「好麻煩還不如規定 agent read」整段丟掉 | Memory（`feedback_simplest_workaround_first`） |
| 4 | 本 session 不知道隔壁 session 在問什麼 | 做（本 commit） |

# Changes Made

- `bin/session-log.py`
  - `neighbors(lp)`：同專案資料夾、24h 內有動、排除自己、最多 5 個 log；每個一行：id 前 8 碼、標題、最後更新時間、最後一句 `[user]`。
  - `pending_ask(jsonl)`：讀 jsonl 尾端 300KB，找沒有對應 `tool_result` 的 `AskUserQuestion`，回傳第一題。只能讀 jsonl：`said` 在 Stop 才跑，卡在彈窗的回合不會 Stop，log 裡沒有它。
  - `cmd_reprint` 簡報尾端加這一段，並寫明兩個用法：使用者問到隔壁談過的題目先讀它的 log；有 ⏳ 的先提醒使用者那邊在等。

# Result

- 真實資料：5 個鄰居 0.01 秒列出；合成 jsonl：未回答 → 回傳題目、已回答 → `None`。
- 沒改 settings.json；`reprint` 本來就掛在 SessionStart(compact|resume)。

# Unsolved Issues

- `[user]` 最後一句可能是 harness 產生的「Answering your earlier questions…」，沒過濾（cosmetic）。
- 只看同一個專案資料夾；跨專案（同一個 repo 從不同 cwd 開）看不到。
