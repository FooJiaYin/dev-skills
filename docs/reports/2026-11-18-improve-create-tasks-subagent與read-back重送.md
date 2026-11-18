# 2026-11-18 improve：create-tasks 執行交給 subagent、apply read-back 重送 people／date

| 問題（sparktoy 11/18 會議建票） | 改法 |
| --- | --- |
| 計畫核准後主對話自己跑 `apply`＋5 次修補＋read-back，使用者：「應該要用 subagent create task」（全域 CLAUDE.md 已有規則，但 §9 沒寫，skill 文字優先） | `skills/create-tasks/SKILL.md` §9 開頭加一行：整段 §9 交給一個 subagent，主對話只收 result.json 摘要與 ✗ |
| `apply` 建完立刻 PATCH people／date，read-back 仍 5/5 回成 bot 帳號與今天；幾分鐘後 MCP 再寫就留住 | `bin/notion-io.py` read-back：people／date 不符時等 2 秒、重送、再讀一次，才記 ✗（新增 `sent_raw` 存原始值；舊 result.json 沒有這欄就不重送） |

沒驗：重送路徑還沒實跑過（本次已用 MCP 手動修好）；下次建票看 ✗ 是否消失。
