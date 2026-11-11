# /improve 2026-11-12：notion-io 建票屬性、dated Update、日期標籤、fetch-task 日期前綴

來源 session：sparktoy 11/11 會議 → 建票 → 舊 plan 整理（7a9c09f2）。

| # | 摩擦（實際發生） | 改了什麼 |
|---|---|---|
| 1 | `notion-io.py apply` 建出的票 Assignee 變成 integration bot、Time 變今天（兩批 7＋8 張都發生，每次都要用 MCP 補） | 建頁後再 PATCH 一次所有 people／date 屬性（含 `[]`、`null`），再讀回；`chmod +x` |
| 2 | LINK 到已實作（Testing／In Review／Completed）的票，使用者要求會議段落放頁尾 `# <date/> Update`，script 只能寫 `# Context`，12 段要另用 MCP 補 | link 列新增 `"update": "YYYY-MM-DD"`；create-tasks §9.2 依目標狀態選 Context 或 dated Update；hard constraint 同步放寬 |
| 3 | `/upload-meeting` 建議的標題 `<mention-date …/>` 存成字面文字 | upload-meeting §1、§5 與 tasks-json.md 範例改 `<date start="…" />` |
| 4 | 使用者要 fetched task 檔名以日期開頭 | fetch-task §3b：`docs/tasks/<YYYY-MM-DD>-<slug>-<hash6>.md`，日期＝Notion 建立日；refresh 先找同 hash6 的舊檔 |

未驗證：#1、#2 只過 `py_compile` 與 `--help`，沒對 Notion 實跑 `apply`；下次建票時看 `✗ read-back` 是否消失。

另：「計畫核准後執行交給 subagent」寫進全域 `~/.claude/CLAUDE.md`（不在本 repo）。
