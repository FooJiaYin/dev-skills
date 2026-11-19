---
session: pimi-launch-implementation (58181c4a-342a-4e35-a066-7c40b519c198), improve-fanout前規劃驗證 (08b4fd52-4070-4822-ac37-a9f1ab1c957b)
---

# improve：fan-out 前先規劃驗證、agent 超時先當成等權限、session log 濾雜訊

# Description

- 回顧 pimi 第一版實作的 session（58181c4a，11/17–11/19，133 個 commit、三次 compact）。那個 session 自己跑過兩次 improve，後段的深入分析在 compact 前沒做完；這次由另一個 session 讀完整份 session log 接著做。
- 取代同日的 `2026-11-19-improve-agent停滯要主動查.md`：那份寫「停滯的原因沒有查出來」，後來對時間查到是在等權限提示，規則已改寫。

# Changes Made

| 檔案 | 現在❌ | 改後✓ |
|---|---|---|
| `docs/agents-and-sessions.md`〈派 agent 之前〉 | 兩條具體做法：派之前看記憶體、整套測試只由主對話跑一次 | 一條上游規則：**fan-out 前先規劃這批 agent 的驗證怎麼進行最有效率**（測試、型別檢查、build、dev server、截圖），做法因案而異；列出要想過的五件事，「誰跑」含「指定一個專門跑驗證的 subagent」；兩條舊規則縮成事例 |
| `docs/agents-and-sessions.md`〈agent 執行中與交件〉 | 超時就查，停滯就停掉 | 派出後定時看；最後事件是「送出指令沒結果」先當成等權限並告訴使用者；brief 不叫 agent 讀工作目錄以外的東西 |
| `skills/improve/SKILL.md` | 從對話記憶找摩擦 | 第一步固定讀 session log（濾掉 `[write]`），並跳過前一次 improve 已落地的 |
| `bin/session-log.py` | `~/.claude/projects/` 底下別的 session 的對話檔每次 Bash 都記成 `[write]`；`[error]` 只有 `Exit code 1`；agent 派出與交件沒有紀錄 | 不記 session 資料（`memory/` 例外）；`[error]` 接上錯誤訊息最後一行；新增 `[agent] dispatch …` 與 `[agent] done … ran= calls= slowest= unanswered=` |

- 不在這個 repo 的：`~/.claude/settings.json` 的 PreToolUse（Agent|Task|Workflow）與 SubagentStop 各加一條 `session-log.py agent`；`~/.claude/CLAUDE.md`〈Self Improve〉加「摩擦當下記 `note "improve: …"`、說出『之後會做 X』的同一步寫進 TODO.md」，以及「驗證跑不過時只寫檔回報」那條加一句指向新規則。

# Result

- **為什麼是一條上游規則**：翻了其他 session（41 個專案、321 份 log 先用「≥3 個 subagent 且使用者有催促」預篩，再加並行峰值 ≥3 的 9 個 session）。出事的五次問題各不相同（多份測試同時跑、每個 agent 各開 server 與截圖、權限擋實測、環境沒套件、產物放暫存），每次事後補一條針對性的規則，下一次換別處出事；brief 先寫清楚驗證範圍的五次都沒出事，而且五次寫法都不同。
- **使用者否決的寫法**：「整套測試只由主對話跑一次」（主對話跑會佔用 context，沒辦法同時討論別的）；「規劃一定要先實際跑一支量時間」（成本在哪用想的就想得到）；「再小的修改也派出去」。
- **驗證**：`session-log.py` 用 58181c4a 的真實 subagent 紀錄測過，那個等權限的 agent 印出 `ran=148m calls=11 slowest=91m Bash …google-cloud-sdk`；對 `~/.claude` 實跑快照，`projects/` 底下 0 筆。
- **未驗證**：`[agent]` 的兩個 hook 還沒在真的 hook 事件上跑過，SubagentStop 的欄位名（`agent_id`、`agent_type`、`agent_transcript_path`）是照慣例寫的。主對話自己的慢指令沒有紀錄。
- **過程中的失誤**：`session-log.py` 第一版用了 Python 3.9 不支援的寫法，約一分鐘內所有 session 的紀錄 hook 都會失敗。
- 沒處理、留給使用者決定：交件前先跑一次使用者流程；`pimi/AGENTS.md` 指向上層 `AGENTS.md`；測試環境的管理員密碼由 agent 產生並存進密鑰庫。
