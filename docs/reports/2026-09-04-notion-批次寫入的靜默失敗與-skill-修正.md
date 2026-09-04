# create-tasks／sync-report：Notion 批次寫入的靜默失敗與六處 skill 修正

## 一眼看懂

```
這次跑 /create-tasks 把 6 場會議 + 8 份報告 + 16 筆行動項（共 32 項）寫進 Notion，
過程中撞到 4 個 skill 沒寫、或寫錯的坑。全部已修進 SKILL.md。

坑 1  設定探索                現在 ❌                        改後 ✓
      AGENTS.md 沒 ## Notion → 我手動爬 workspace 6 次      → 一律 dispatch /setup-notion
                              並把「guest id 查不到」當成      （它會匯入 ../AGENTS.md 的
                              阻塞問題去問使用者                ## Notion，roster 就在裡面）
      實際代價：整個前半場把已經躺在磁碟上的 assignee 當無解

坑 2  寫入不落地              現在 ❌                        改後 ✓
      sync-report 明寫        blind re-write，不用回查        → 批次寫完用「一次 SQL
      "don't waste tokens                                      read-back」掃全部新列再修
       on a verify-fetch"
      實測：6 次 update_properties 回 {page_id} 無錯，但沒生效
            C1/C9/B1/B3 assignee 退回 OAuth 帳號、B3/B8 日期停在今天

坑 3  沒送的欄位也會被寫       現在 ❌                        改後 ✓
      skill 只警告「有送 Time  14 筆從頭到尾沒送 Time 的      → 要空白必須顯式送
      但沒送 is_datetime」     任務被 create-pages 填今天       "date:Time:start": null

坑 4  表格錨點                現在 ❌                        改後 ✓
      §9.4 說 old_str 用      本地 `| P0 | … |` 上傳後       → old_str 取自上傳後的
      「原文 byte-exact」      在 Notion 是 <table><td>，       fetch，錨在單一 <td>；
                              一定 miss → 整批 10 個 op        同格多任務 = 1 個 op 掛
                              一起失敗                          多個 mention

坑 5  平行門檻                現在 ❌                        改後 ✓
      §9 只在「body 組裝」    6 份 11–63KB 的檔案被讀進      → 主 agent 只做規劃；
      時 fan out              主 context 再原樣吐回 create     大型本地檔讓 subagent
                              呼叫，序列做兩份就被使用者打斷    自己讀、自己呼叫 MCP
```

# Description

- 本次任務：把 `sparktoy` 專案累積的 6 場會議記錄、8 份開發報告、以及 2026-09-02 會議的 16 筆行動項，全部寫進 Notion 並掛到新建的專案頁「龍杰國際 / Sparktoy」。
- 過程中 `/create-tasks`、`/sync-report`、`/setup-notion` 三個 skill 交互作用，暴露出四類問題：設定探索順序、MCP 寫入的可信度、屬性預設值、以及平行化門檻。
- 本報告只記錄 **skill 層面的修正**；Notion 端的落地結果記在 `sparktoy/docs/tasks/_plan-2026-09-02-龍杰國際-sparktoy.md`（28 列都回填了 `✅〔notion:<id>〕`）。

# Changes Made

## `skills/create-tasks/SKILL.md` — 5 處

| 位置 | 修改 |
|---|---|
| §1 Resolve config | 新增「**Dispatch it — do not improvise around it**」：禁止手動 `notion-search` / `notion-fetch` 爬 workspace 重建 DB URL；並註明 `/setup-notion` 會匯入 parent 目錄 `../AGENTS.md` 的 `## Notion`（**含 roster**），那裡常有 workspace user-search 查不到的 guest user-id。 |
| §9.1 Time 欄位 | 補上「**Omitting `Time` entirely does NOT leave it blank**」— `create-pages` 仍會蓋今天；要真正空白得事後顯式送 `"date:Time:start": null`。並把原本的「fetch 一頁抽驗」改指向新的批次回查規則。 |
| §9.4 Annotate | 新增：commitment 來自 markdown 表格時，`old_str` **必須**取自上傳後的 `notion-fetch`（Notion 存成 `<table><tr><td>`），錨在單一儲存格；同格對應多個任務時是**一個 op 掛多個 `<mention-page>`**，不是多個 op（第一個替換掉後其餘全 miss，一 miss 整批失敗）。 |
| §9 Execute | 新增「**Parallel MCP writes**」：主 agent 負責規劃與抽取，`notion-create-pages` / `notion-update-page` 本身可以 fan out。來源是多個大型本地檔（單檔 >10KB 或總量 >50KB）時，派 subagent 自己讀檔、自己呼叫 MCP，不要把檔案內容經主執行緒往返。 |
| Hard constraints | 把「MCP write responses echo input」那條擴寫成「**post-create `update_properties` is not durable either**」：批次建立＋後續 update 之後，用**一次 `notion-query-data-sources` SQL read-back** 掃全部新列（Name／Status／Type／Time／Assignee／Priority）再修；per-page fetch 在 batch size 下太貴，blind re-write 不夠。 |

## `skills/sync-report/SKILL.md` — 1 處

| 位置 | 修改 |
|---|---|
| §5 Create new 分支 | 刪掉「**Don't waste tokens on a verify-fetch … blind re-write, no re-fetch needed**」這個明確錯誤的指示。改為：blind re-write 照做，但**必須用一次 SQL read-back 驗證**（實測會靜默不生效：guest assignee 退回 OAuth 帳號、日期停在今天）。同時補上「未送 `Time` 不等於空白」。 |

# Result

- 6 處編輯全部套用並驗證（兩檔各 `grep -c "SQL read-back"` = 1）。
- Notion 端 32 項全部落地並回查通過：6 場會議日期正確、24 筆任務的 Type／Status／Time／Assignee 正確、10 個 inline `<mention-page>` 全部命中、`Tasks` relation 16 筆。
- 本次靠事後 SQL 回查**救回 6 筆錯誤寫入**（14 筆日期 + 4 筆 assignee），全部是 subagent 回報「update OK」但實際沒生效的。若照修改前的 skill 指示（不回查），這 6 筆會直接以錯誤狀態留在 Notion。

# Unsolved Issues

- **命名規則沒寫進去**：本次還有一個發現是任務 `Name` 不該用內部黑話（「產品建檔第一刀」使用者看不懂），但使用者指示只寫平行那條，命名規則刻意未納入 §4。
- **`update_properties` 為何靜默失敗未查明**：只知道現象（回 `{page_id}` 無錯但不生效），沒有排除是 rate limit、async 佇列、還是 guest 權限造成。目前的對策是「一律回查修正」而非根治。
- **同檔案混著多次 session 的未提交改動**：`create-tasks` / `sync-report` 這兩檔在本次 commit 前就有前幾次 improve 留下的未提交 hunk（Chat-app source 整節、plan 重讀規則、ambiguous reply 規則），本 commit 一併帶入。repo 內另有 3 個 modified SKILL.md 與 3 個 untracked 路徑仍未提交。
- **`dropout/main` 與 `main` 分歧 1/1**：本次 push 目標是追蹤上游 `origin/main`（同步、fast-forward）。`dropout` 那個 fork 的分歧未處理，留給 owner 決定。
