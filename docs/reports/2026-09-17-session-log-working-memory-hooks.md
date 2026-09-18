---
session: 2026-09-17-context-management-設計討論 (9f0295b0-6a7f-461a-8d7a-ed85f717c124)
---

# Plan

# Session working memory：`<session>.log.md` ＋ compact 重印

```
現在 ❌  compact → LLM 摘要猜重點 → 你的決定、我的結論、未 commit 檔靠運氣活下來
        uncommitted-by-session.sh 用正規表達式猜寫入路徑 → 目錄前綴展開 → 別的 session 的髒檔混進來

改後 ✓  hook 邊做邊寫 <session>.log.md（時間順序、append-only、人機都可讀）
        PreCompact 有未 commit → 擋一次 → Stop hook 讓我問你 commit／improve → 放行
        SessionStart(compact|resume) 把 log.md 全文重印回 context（30k 才截）
```

## Context

98 個 session 只 compact 過一次，因為壓縮後忘太多；不 compact 就長到 900k。忘掉的東西其實都在磁碟（transcript、git），只是沒人在壓縮後印回來。現有 compact hook 又會把別的 session 的檔混進來（Bash 指令裡任何絕對路徑都被當寫入目標，目錄前綴展開）。目標：一份 per-session 工作紀錄，機械寫、機械印，讓手動 `/compact` 變得可信。autocompact 維持預設門檻，不改。

## 決定（已討論定案）

| 項 | 決定 |
|---|---|
| 檔 | `~/.claude/projects/<proj>/<session-id>.log.md`，一檔，時間順序，append-only |
| 行格式 | `[HH:MM tag] 內容`；多行內容延續到下一個 `[` 開頭行 |
| 標籤 | `user` `assistant` `ask` `skill` `write` `error` `note` `compact` |
| `assistant` | 只收回合結尾那一則，過場短句不收 |
| subagent | 對話不進 log；其寫入以 `write` 記，尾綴 `agent=<id>` |
| `write` | 寫入當下記帳：路徑、repo、工具、寫後 sha。Bash 用前後 `git status`＋`hash-object --stdin-paths` 差集，不解析指令 |
| 重印 | compact／resume 後全印；>30k token 才從最舊 `assistant` 縮成首行。_(03:30 改)_ hook stdout 硬上限 10k 字元，改為：hook 印簡報（指標、未 commit 表、commit、「先 Read 完再回話」指令），全文按時間重排、`[write]` 連續段摺成一行後寫到 `<sid>.reprint.md`，由 agent 分段 Read |
| compact 前 | PreCompact(auto|manual)：log 有未 commit `write` 或本輪未 improve → exit 2 擋、寫 marker；Stop hook 見 marker → block 一次，理由含清單，我用 AskUserQuestion 問 commit／improve；答完清 marker，下回合放行 |
| report transcript | 不再獨立產生；`/report transcript` 改成「複製 log.md 的 user/assistant/ask 行＋密鑰過濾」的薄殼 |
| 舊 hook | `uncommitted-by-session.sh` 退役，功能由 log 的 `write` 行取代 |

## 檔案

| 檔 | 動作 |
|---|---|
| `dev-skills/bin/session-log.py`（新） | 子命令：`record`（PostToolUse 記 write/error/skill）、`snapshot`（PreToolUse Bash 存 git 狀態到 tmp）、`said`（Stop 時從 transcript 追加 user/assistant/ask；重用 `report/export-transcript.py` 的 `read_entries`、`clean_text`、`build_turns`、`compact_note`）、`reprint`（SessionStart 印全文）、`precompact`（檢查＋marker）、`stop-check`（marker → block JSON） |
| `~/.claude/settings.json` | hooks：PreToolUse(Bash)→snapshot；PostToolUse(Bash\|Write\|Edit\|MultiEdit\|NotebookEdit)→record；PostToolUseFailure→record error；Stop→said 然後 stop-check；PreCompact→precompact；SessionStart(compact\|resume)→reprint。移除舊 compact hook |
| `dev-skills/skills/report/SKILL.md` | §transcript 改讀 log.md；report／task 檔 frontmatter 加 `session: <id>`，讓 report 能連到 `<id>.log.md` |
| `dev-skills/skills/wrap-up/commit.md` | 「本 session 寫過的檔」改讀 log `write` 行 |
| `dev-skills/bin/uncommitted-by-session.sh` | 刪 |
| `~/.claude/CLAUDE.md` | 一行：驗證通過或做決定時寫 `[note]`（透過 `session-log.py note "…"`） |

## 順序

1. `session-log.py record/snapshot/said/reprint` ＋ hooks 接線（先不動 PreCompact/Stop）
2. 用一個活著的 session 手動 `/compact`，問三題（未 commit 什麼、你改過哪些決定、下一步）對 transcript
3. 通過 → 加 `precompact`／`stop-check`（autocompact 門檻不動）
4. 有 log 用 log、沒有 fallback jsonl，依序：commit.md 改 grep `[write]` → `/report` 讀 `[user]/[ask]/[note]/[write]`、transcript 模式改過濾 log → `/improve` 讀 `[error]`＋緊接的 `[user]` → find-session 先掃 log.md → SessionStart(startup) 印同 branch 最近 3 個 log 的標題行 → 刪舊 compact hook

## 驗證

- `record`：一條 `cd repo && cat > x` 只記 x；`ls /repo/docs/ ; … > /tmp/y` 不記 repo 任何檔
- 拿今天 12 個 transcript 跑舊腳本 vs 新 `write` 行，列「舊 N 檔 → 新 M 檔」
- 手動 compact 後 `/context` 看重印段大小；三題答案對 transcript
- PreCompact 擋下時 Stop 只問一次（`stop_hook_active`）；乾淨時直接壓
- 每條 Bash 多花 <0.3s（ibadminton 63 髒檔用批量 hash 量一次）

## 未定

- settings.json 接線不在版控；`~/.claude` 是零 commit 的 repo，要不要開始 track settings＋hooks 由你定
- improve 每次檢查點都提，還是只在有 `error` 時提（先做前者）

# Session working memory：`<session>.log.md` ＋ compact 重印 hooks

```
現在 ❌  compact → LLM 摘要猜重點 → 決定、結論、未 commit 檔靠運氣活下來
        uncommitted-by-session.sh 從 Bash 指令猜寫入路徑 + 目錄前綴展開 → 別的 session 的髒檔混進來
        jsonl 30 天刪、4MB 人讀不動；report transcript 要手動匯

改後 ✓  hook 邊做邊寫 ~/.claude/projects/<proj>/<session-id>.log.md（時間順序、append-only、人機可讀）
        SessionStart(compact|resume) 全文重印回 context（30k token 才截）
        寫入當下 git 差集記帳：只有自己寫的檔；Edit 前 hook 警告「別的 session 寫過這檔」
        report／find-session／wrap-up 改讀 log；jsonl 保留 3650 天
```

# Description

- 把 [設計討論](../../../docs/reports/2026-09-17-context-management-設計討論.md)（在 `~/agent-skills/docs/reports/`，不屬於任何 repo） 定案的 working memory 做出來：一支腳本、七個 hook 掛點、四個 skill 改讀 log。設計討論的完整脈絡在那份；這裡只列每個決策的由來。
- 不含：`/improve` 讀 log（使用者排除）；PreCompact 擋＋Stop 問（step 3，待 step 2 後決定）；archive。開場索引原本排除，後來因「我想丟上一個 session 的 log 給下一個 session，但都藏在 .claude 裡很麻煩」而加回，列 5 個（「我可能同時開 5 個 session」）。

## 設計決策與由來

| 決策 | 由來 |
|---|---|
| 一個檔、時間順序、`[MM-DD HH:MM tag]` 行首、八標籤 | 原提案拆四檔；使用者「拆那麼多檔案好嗎？還是直接時間順序」。時間線保住因果（改 → 錯 → 你糾正 → 我改）。日期前綴是我加的，session 常跨天 |
| 使用者與 agent 原話都逐字存、都全印 | 使用者「我和你的原話都要保留」、「沒關係還是重印吧，本來體積就小，你不要廢話那麼多就行」。量過：使用者文字中位 624 字、agent 27.7k 字（44×）；200k 窗內全印約 5% |
| `[assistant]` 只收回合結尾那一則 | 過場短句（「我先看看…」）是廢話來源，也是 log 體積主因 |
| 寫入當下記帳，Bash 用前後 git status＋hash 差集 | 使用者「我只要這個 session 的 uncommitted file，不要其他 session 的混進來」→ 驗證 12 個 session 全部被目錄前綴誤判 → 使用者「不可漏也不要混」→ 事後猜做不到，只能寫入時記 |
| hook 前的歷史從 transcript 補：對話全補，Write／Edit／Skill／error 補，Bash 寫入不補 | 使用者擔心「舊 session 跑 compact 不就 hook 前的對話沒了」。Bash 沒快照，補就是回到猜，標「無法比對」 |
| 第一行存標題／id／專案／branch，可改寫 | 使用者「session log 也要存 title 吧」；標題取 jsonl 最新 rename |
| compact／resume 後全印，不分段 | 使用者誤以為「取最後一個 [compact] 之後」是丟掉之前；澄清後決定全印 |
| autocompact 門檻不動 | 使用者「我不要 200k，恢復預設」；本來就沒設 |
| report transcript 由 log 取代 | 同一份原始資料兩種視圖；使用者「這樣感覺不用 report transcript 了」 |
| task 檔＝report；report 加 `session:` frontmatter | 使用者「task 就是 report」、「report 是不是要寫 session id 呀…這樣有辦法找到 log 嗎」 |
| Edit 前警告別的 session 寫過 | 使用者問「這個現在有哪裡有讓 agent 注意嗎」→ 沒有 → 做成 PreToolUse additionalContext，不擋不問 |
| footer hook 搬進 dev-skills/bin | 使用者「require session footer 怎麼沒進版控」；原在 `~/.claude/hooks/`，`~/.claude` 是零 commit repo |
| `cleanupPeriodDays: 3650` | 使用者「馬上改 settings」；8/18 前的 jsonl 已被掃掉 |
| 其他 skill 改讀 log，沒 log 退回 jsonl | 使用者「我想要在其他場合/skill 也用 log 代替 jsonl 節省 token」、「除了 improve 和新 session 開場其他都要做」 |

# Changes Made

- **`dev-skills/bin/session-log.py`**（新，727 行）— 子命令：
  - hook：`snapshot`（PreToolUse Bash）、`record`（PostToolUse Write/Edit/MultiEdit/NotebookEdit/Bash/Skill、PostToolUseFailure）、`said`（Stop；從 transcript 補 `[user]/[assistant]/[ask]/[compact]`，並 backfill hook 前的 Write/Edit/Skill/error；批次按時間排序）、`reprint`（SessionStart compact|resume；`said` 後印全文＋未 commit 表＋本 session commit）、`warn`（PreToolUse Write/Edit；掃他人 log 的 `[write]`）
  - hook：`index`（SessionStart startup|clear|fork；列本專案最近 5 個 log：標題行、時間範圍與計數、最後 `[note]`、最後 `[user]`、路徑）
  - CLI：`note "…"`、`show`、`writes`（wrap-up 用）、`export [-o]`（可讀 transcript，密鑰過濾）、`backfill --all`（一次把 107 個既有 jsonl 產出 log，8.8 秒、3.9 MB；Bash 寫入除外）
  - 重用 `skills/report/export-transcript.py` 的 `read_entries`／`clean_text`／`blocks_of`／`result_to_text`／`tool_name_map`／`compact_note`
  - 過濾 harness 假 user 訊息（subagent 回報、task-notification、「hasn't heard from you」）；拆「sent a new message while you were working」外殼
- **`dev-skills/bin/require-session-footer.py`** — 從 `~/.claude/hooks/` 搬入；標題先讀 log 第一行，再退回 jsonl
- **`dev-skills/bin/uncommitted-by-session.sh`** — `git rm`（功能由 log `[write]` 取代）
- **`~/.claude/settings.json`** — hooks：PreToolUse(Bash)→snapshot、PreToolUse(Write|Edit|MultiEdit|NotebookEdit)→warn、PostToolUse(Bash|Write|Edit|MultiEdit|NotebookEdit|Skill)→record、PostToolUseFailure→record、Stop→said、SessionStart(compact|resume)→reprint、SessionStart(startup|clear|fork)→index；拔舊 compact hook；footer hook 改指 dev-skills/bin；`cleanupPeriodDays: 3650`。備份 `settings.json.bak-*` 四份
- **`dev-skills/skills/find-session/scripts/search.py`** — 新增 `scan_log()`：有 `<sid>.log.md` 就掃它（`--touched` 讀 `[write]`），沒有才掃 jsonl；SKILL.md 補一段
- **`dev-skills/skills/wrap-up/commit.md`** — 未 commit 清單改 `session-log.py writes`；「誰寫的」說明 find-session 先讀 log；footer 標題改讀 log 第一行
- **`dev-skills/skills/report/SKILL.md`** — 合成前先讀 log；transcript 模式改 `session-log.py export`、不預設提交匯出；guideline 9：frontmatter `session:`
- **`~/.claude/CLAUDE.md`** — Self Improve 段加一行：驗證通過或做決定時 `session-log.py note "…"`
- **`~/.claude/plans/lively-drifting-cocoa.md`** — plan；step 3 改「門檻不動」、step 4 展開成 skill 清單

_(09-18，第二個 commit)_
- **`session-log.py reprint`** — 改印 <1k 簡報（指標、未 commit 表、本 session commit、「先用 Read 讀完再回話」），全文按時間重排、`[write]` 連續段摺一行後寫 `<sid>.reprint.md`；Read 每頁 25k token 自動分頁，`cat` 超過 30k 字元會被存檔所以明文禁止
- **`session-log.py` `[write]`** — `pre=`／`sha=` 一對 blob（`hash-object -w`）；PreToolUse(Write|Edit…) 也跑 `snapshot`；新 CLI `writes --mine <file> [--stage]`；`writes`／`show` 接受 id 前綴；跳過無 HEAD 的 repo
- **`session-log.py` `[web]`**（第九個標籤）— PostToolUse(WebFetch|WebSearch) 記 URL／query，含 subagent；使用者：「webfetch 也要被記錄，才有 reference source」
- **`find-session/scripts/search.py`** — `--open [N]`、`--open-id <uuid 前綴>` 用 `code` 開 `<sid>.log.md`；compact 輸出多一欄 `log`／`-`；行正則加 `web`。使用者：「find-session 可以支援開啟 log 嗎，不然很麻煩」（log 藏在 `~/.claude` 隱藏資料夾）
- **`wrap-up/commit.md`** — co-edited 段換成 `writes --mine --stage`，手工流程降為 fallback
- **`report/SKILL.md`** — `# References` 從 `[web]` 拿
- **`~/.claude/settings.json`** — PreToolUse(Write|Edit|MultiEdit|NotebookEdit) 加 `snapshot`；PostToolUse matcher 加 `WebFetch|WebSearch`

# Result

合成 hook JSON 測試（全部通過）：

| 測 | 結果 |
|---|---|
| 只讀＋導向 /tmp 的 Bash | 記 0 筆 |
| Bash 在 repo 建檔 | 記 1 筆，sha 正確 |
| Write／Skill／PostToolUseFailure | 各記對應標籤 |
| 凍結 transcript 跑 `said` 三次 | 87→87→87，順序 0 筆亂序 |
| harness 假 user 訊息 | 0 筆混入；插話原句拆出 |
| a5bd9f6a（有 rename、有 compact） | 標題、branch、`compact (auto, 1,013,317 → 20,866)` 抓到 |
| cleanstation 凍結副本 backfill | 48 write／3 skill／2 error，兩跑不重複，重印標「hook 前寫的，無法比對」 |
| `writes`／`warn`（他人有警告、自己無）／`export`（118 段）／`redact`（三種樣式）／footer hook 讀 log 標題 | 通過 |
| find-session `--touched`、`--topic` 經 log 命中 | 通過 |

_(03:04 本 session 自己 compact)_ 摘要層清楚，`[write]` 記帳正確（7 檔全列、另一 session 3 檔沒混入），但重印 15 萬字元撞上 **hook stdout 10,000 字元硬上限**（官方 hooks 文件，無設定可調），實際只注入 2KB 預覽。試過拆 6 條 hook 各印一段（時間順序可保，用段頭時間對回來），使用者裁定「好麻煩還不如規定 agent read」→ 改成簡報＋`.reprint.md`。順便發現並修了：log 是 append 順序（write 即時、user/assistant 在 Stop 落地）重印前要按時間重排；`~/.claude` 零 commit repo 的 230 個 untracked 全被列成「未 commit」，跳過無 HEAD 的 repo。

_(09-18 01:25 加)_ **`[write]` 存 pre／post blob，`writes --mine` 機械拆 co-edited 檔。** 起因：使用者問「write 不記改哪一行？commit 時要去 jsonl 找？」（同一題在 c085e38c 那個 session 也問過一次）。只存寫後 sha 會混：我寫之前檔裡若已有別人的 hunk，寫後 blob 就含他的。解法是每次寫入記一對：`pre=`（寫前）`sha=`（寫後），`hash_files` 改 `hash-object -w` 把內容存進該 repo 的 `.git/objects`（unborn repo 如 `~/.claude` 不存）；Write／Edit 加 PreToolUse `snapshot` 存寫前 blob，Bash 寫入的 pre 取前快照、沒在快照裡就取 `HEAD:<rel>`、新檔記 `new`。一次工具呼叫是原子的，所以 diff(pre, sha) 純粹是我的；`writes --mine <file> --stage` 把連續無人插手的寫入合成 span，`git merge-file` 依序套到 HEAD，產出「HEAD＋我的 hunk」blob 並 `update-index`，工作樹不動，commit 不帶 pathspec。gc 兩週清 dangling blob，夠 commit 用。throwaway repo 測試：別人在我之前、之間、之後各改一行，staged diff 只有我的兩行；新檔也走同一路。舊紀錄（無 `pre=`）或 blob 被 gc 時明確拒絕並指回 commit.md 手工流程。順手修：`writes` 同檔兩種路徑寫法（`/tmp` vs `/private/tmp`）重複列、`writes <id 前綴>` 查不到。

實機：hook 改 settings 後**不用重開就生效**。cleanstation session 6b9c0138（23:26 開）在 02:20 手動 `/compact`，log 48 筆、重印注入 transcript、三題（未 commit／改過的決定／下一步）答出 8 條使用者決定；本 session 自己的 log 到 02:49 有 175 筆。發現並修了一個順序 bug（`[compact]` 排在 `/compact` 那句前，jsonl 本身順序如此 → 批次按時間排序）。

## 每個操作的 token／時間／安全影響

| 操作 | Token | 時間 | 安全／資訊 |
|---|---|---|---|
| **compact** | ＋<1k 簡報 ＋ agent Read 全文（本 session 70k 字元、約 6 次 Read） | — | ✅ 原話、未 commit 全回來；仍可能丟：我的中途結論（沒寫 `[note]` 的話） |
| **resume（閒置回來）** | 同 compact | — | ✅ 同上；之前什麼都沒有 |
| **每條 Bash** | 0 | ＋0.1–0.3 秒 | ✅ 寫了什麼精確記帳；⚠️ 同秒同 repo 併發會誤歸 |
| **每次 Edit／Write** | 0（命中時 ＋幾行） | ＋0.05 秒掃 log | ✅ 別的 session 寫過會被警告 |
| **每輪結束（Stop）** | 0 | ＋0.2 秒掃 transcript | ✅ 對話落地，jsonl 刪了也在 |
| **wrap-up 未 commit 清單** | −（不再貼 find-session 的長輸出） | −（一個指令） | ✅ 不混別人的檔；⚠️ hook 前的 Bash 寫入漏 |
| **/report 合成** | −（讀 30KB log 而非回想整個 context） | — | ✅ 引原句、compact 後也能寫 |
| **/report transcript** | 0 | −（過濾 vs 解析 4MB） | ✅ 密鑰過濾；⚠️ 沒有 `--full` 的 tool 輸出 |
| **find-session** | −（命中片段小） | −（掃 30KB vs 4MB） | ✅ `--touched` 精確；舊 session 仍走 jsonl |
| **git commit** | 0 | — | ✅ footer 標題來自 log，hook 進版控 |
| **磁碟／備份** | — | — | ✅ 不再 30 天刪；❌ 仍無備份，5 GB／年 |
| **我的中途結論** | — | — | ❌ 唯一沒機制保證的：靠我寫 `[note]` |

一句話：多花的是 compact／resume 各一次 25k 和每條指令零點幾秒；省的是每次回顧型操作不用把整段 context 當記憶；可能流失的只剩「我沒寫 note 的判斷」和「hook 前的 Bash 寫入」。

# Unsolved Issues

- ~~PreToolUse→PostToolUse 快照配對未實戰驗證~~ _(09-17 03:10 已驗)_：本 session commit 前 `writes` 列出 7 檔全對、另一 session 的 3 檔沒混入；09-18 的 Edit 在 log 裡有 `pre=`／`sha=`，`git cat-file` 兩個 blob 都取得回。
- ~~dev-skills 待 commit 檔共編~~ _(已解)_：`0a3c0e2` 用 hash-object 只放我的三段；另一 session（be36a58b）隔天 commit `4eb7115`，commit 前有讀 `.reprint.md` 並核對沒倒回我的 hunk。
- **subagent 回報不進 log**：hand-back 以 `isMeta` user 訊息進 transcript，被 harness 過濾丟掉；survey 型 report 需要它。兩案待選：A `[agent]` 全文進 log、view 只印首 300 字；B 只記指標到 `subagents/agent-<id>.jsonl`。
- **`[assistant]` 只收每回合最後一則**：帶圖的中途說明會掉（01:37 那則就是）。提案：有 code fence／表格／超過 300 字的都收，待使用者裁定。
- **重印靠 agent 遵守**：簡報要求先 Read `.reprint.md`，沒有機械保證。
- 舊 session 的 WebFetch／WebSearch 沒回填進 log。
- 同一題在兩個 session 各答一次（本 session 與 c085e38c 都推導了 pre／post blob）：「別的 session 在討論什麼」目前只有 `index` 開場那五行，沒有主題層級的提醒。
- step 3（PreCompact 擋＋Stop 問 commit／improve）待決；預設門檻下只影響手動 `/compact`。
- `~/.claude/settings.json` 的接線仍不在版控；`~/.claude` 零 commit repo 的用途待定。
- archive 到 `~/.claude` 外未做；這台 Mac 沒有任何備份。
- 快照期間他 session 寫同 repo 會誤歸到本 session（罕見，未處理）。
- `warn` 只攔 Write／Edit 工具，Bash 直接寫檔不提前警告（刻意，避免猜路徑誤報）。

# Suggested Doc Updates

_(`/update-docs` propose-only，尚未套用)_

Detected docs layout: `README.md`（skill 表＋Folder Structure）、`AGENTS.md`、`docs/reports/`；沒有 hooks／bin 的文件。

| 檔 | 提案 |
|---|---|
| `README.md` Utilities 表 find-session 列 | 補「`--open` 直接在編輯器開該 session 的 log」 |
| `README.md` Folder Structure | 加 `bin/`：`session-log.py`（session log hooks＋CLI）、`require-session-footer.py`（commit footer hook）、`sync-to-plugin-cache.sh` |
| 新檔 `docs/hooks.md` | `~/.claude/settings.json` 的接線表（事件 → matcher → 指令），因為 settings 不在版控，換機器時只能照這份重建；附 log 九個標籤與 `[write]` 的 `pre=`／`sha=` 格式 |

