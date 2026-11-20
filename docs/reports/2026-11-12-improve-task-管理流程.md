# /improve 2026-11-12：task 管理流程

來源 session：sparktoy 11/11 會議 → 建票 → 舊 plan 整理（7a9c09f2）。兩輪 /improve 合併為一份報告（第一輪 commit `b4524f4`）。

稽核 12 份 `_plan-*.md`：9 份有沒建／沒接會議的列，標頭還寫「尚未執行」；10/14 會議頁 Tasks 是空的；同一會議被兩個 session 各寫一份 plan；8 個 task 檔在報告寫進 code repo 後仍留在父資料夾；兩批建票（7＋8 張）的 Assignee／Time 都要手動修。

## 改了什麼

| # | 摩擦（實際發生） | 改了什麼 | 檔案 |
|---|---|---|---|
| 1 | `apply` 建出的票 Assignee 變 integration bot、Time 變今天 | 建頁後再 PATCH 所有 people／date 屬性（含 `[]`、`null`）再讀回；`chmod +x` | `bin/notion-io.py` |
| 2 | 已實作的票要把會議段落放頁尾 `# <date/> Update`，script 只能寫 `# Context` | link 列 `"update": "YYYY-MM-DD"`；§9.2 依目標狀態選 Context 或 dated Update；hard constraint 同步 | `bin/notion-io.py`、`create-tasks/SKILL.md`、`tasks-json.md` |
| 3 | 標題 `<mention-date …/>` 存成字面文字 | 改 `<date start="…" />` | `upload-meeting/SKILL.md` §1 §5、`tasks-json.md` |
| 4 | fetched task 檔名要以日期開頭 | `docs/tasks/<YYYY-MM-DD>-<slug>-<hash6>.md`，日期＝Notion **Time** 欄起日（空就用建立日）；首次 fetch 定名，refresh 依 hash6 找舊檔不改名 | `fetch-task/SKILL.md` |
| 5 | plan 執行一半沒留痕跡，殘留列沒人接 | `apply` 在 plan .md 標頭寫 `> **執行狀態**` 行；下次 `/create-tasks` 先撈舊 plan 未完成列一起列出，全解決後舊 plan 進 archive；只有 TODO 或使用者明說延後的才進 TODO.md | `bin/notion-io.py`、`create-tasks/SKILL.md` §3 §9.6 |
| 6 | 會議晚於建票才上傳，會議頁 Tasks 是空的 | 上傳後找以此會議為來源的 plan，把 ✅ 的票補上 Discussions | `upload-meeting/SKILL.md` §7 |
| 7 | 同一會議兩份平行 plan | 已有同來源或重疊列的 plan 就延用，標 `moved → <plan>` | `create-tasks/SKILL.md` §3 |
| 8 | 報告在 code repo、task 檔在父資料夾，rename 沒作用 | 也去父資料夾 `docs/tasks/` 找，`mv` 進 code repo 的 `docs/reports/`；檔名用報告日期，先去掉 task 檔的日期前綴 | `report/SKILL.md` 步驟 5 |

全域 `~/.claude/CLAUDE.md`（不在本 repo）另加兩條：計畫核准後執行交給 subagent；回答 task 的測試／QA 結果是交付物，寫進 `docs/reports/` 並同步 task。

## 未驗證

- #1、#2、#5 只過 `py_compile`／`--help`；`plan_status()` 在暫存檔單獨測過（插入、取代、檔案不存在）。沒對 Notion 實跑 `apply`——下次建票看 `✗ read-back` 是否消失、plan 標頭是否出現執行狀態。
