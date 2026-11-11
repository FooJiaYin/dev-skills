---
session: code-review 精簡化討論 (d9a99d25-1efe-4370-93ac-c670a8fbde8f)
---

# Plan

# Plan: review tiers + /align + TODO.md

## 摘要

```
現在 ❌                                         改後 ✓
wrap-up ─► /code-review                         wrap-up ─► quick-review（每次）
           6 agents + Haiku scorer × N                     ① codex review（自由審，不給清單）
           幾乎每次被跳過                                    ② resume 同 thread + commons 清單（只報新的）
                                                           + gitleaks（有裝才跑）→ REVIEW.md
                                                ─► /align end ─► 基準清單逐條核對 ─► TODO.md
merge 前 ─► （沒有）                             merge 前 ─► code-review（隨 diff 派 agent + 二元 verifier）
需求漏掉／做歪 ─► 人看畫面才發現                  plan 前 ─► /align start（逐段往回比，掉的項目逐條處理）
未完成事項 ─► 埋在對話                            未完成 ─► TODO.md（由核對產生，不是 agent 自報）
```

| 檔案 | 動作 |
|---|---|
| `shared/review/commons.md` | 🆕 註解規則＋基本標準（全）＋安全清單（全）＋「/improve 新增」區 |
| `skills/quick-review/` | 🆕 SKILL.md ＋ `run.py`（跑兩輪、取 thread_id、命名、寫 REVIEW.md） |
| `skills/align/` | 🆕 SKILL.md（start / end；TODO.md 格式） |
| `skills/code-review/` | 改：description、路由、verifier、standards 讀 commons、移除 plan-adherence |
| `wrap-up/full.md`、`quick.md` | 改：step 3 → quick-review ＋ /align end；Quick 加 review |
| `sync`、`create-tasks`、`report`、`update-docs`、`improve` | 小改（各一段） |
| `README.md`、`~/.claude/CLAUDE.md` | 表格＋安裝清單；一行規則 |
| 延後 | PR/CI tier、`docs/site`、design skill 那側（另一個 session） |

## Context

- 10/28 回顧報告 §8：`/code-review` 9/24 之後沒跑過，wrap-up 跳過約 16–17 次（成本固定又高；已有其他證據）。6 個 agent 也不涵蓋實際發生的落差（需求對齊、UI 對齊）。
- §4／§5：利潤率（做歪）、ZIP（漏掉）、10/28「fix all mentioned in 10/22 meetings」——都是人看畫面才發現；「做完沒說」的 TODO.md 由停下的 agent 自己寫，沒有分母。
- 本 session 討論定案：quick 用 codex review（實測：第一輪漏掉 hard-coded key，resume 補檢查抓到）；名稱維持 quick-review／code-review、description 寫使用場景；commons 放 `shared/review/`、全量＋/improve 可加；需求鏈 transcript → meeting notes → task → plan（段可缺），新 skill `/align`；TODO.md 規則進全域 CLAUDE.md；PR tier 延後；gitleaks 有裝才跑；quick 不用 impeccable。

## 前置：分支

`dev-skills` main 有其他 session 未 commit 的改動（`README.md`、`headless-shots`、`rename-session`、`upload-meeting`），而本計畫也要改 README。→ 開 worktree `review-align` 分支（`git worktree add ../dev-skills-review-align -b review-align`），全部在那裡做；README 合併時再處理。

## 1. `shared/review/commons.md`（新）

三輪共用、quick／code-review／（未來）pr-review 都讀。開頭一句：**「這是下限不是範圍——先照你自己的判斷審完，再用這份補漏」**。

- **① 註解規則**：只評 `+`/`-` 行、不報既有問題；每條寫出觸發情境（輸入／狀態／後果）；禁「please verify」；severity 四級；忽略風格除非違反下方標準。（從 `code-review/SKILL.md` 的 Tone Constraints 搬過來，code-review 改成引用）
- **② 基本標準**（全）：重用既有 utility／元件；UI 字串語言對齊鄰近字串；UI 不出現內部代號；derived state 明確處理空／零；大小／數量限制在 server action／RPC 驗；同一 state 兩處推導時 guard 要對稱；暫存產物不進 repo；批次 DB 寫入／migration 有預覽或 guard。
- **③ 安全清單**（全）：hard-coded secret／`.env`；SQL／command／path injection；授權與 RLS／policy；XSS（`dangerouslySetInnerHTML`、未跳脫輸出）；server-only 值流到 client（service-role key、server env）；CORS／cookie／redirect；`eval`／不安全反序列化。
- **④ `## Added by /improve`**：空區，/improve 寫入的新規則放這（每條一行＋來源日期）。
- 專案層：`<repo>/docs/review-standard.md`（可選）附加在 commons 之後，優先於 commons。

## 2. `skills/quick-review/`（新）

**description**（定案稿）：Lightweight review run at the end of EVERY session/commit — invoked by /wrap-up (Full and Quick). `codex review` on this session's uncommitted diff (cross-model), then resumes the same Codex thread with the shared review commons so the checklist doesn't anchor the first pass. Writes REVIEW.md. For a whole branch before merge, a big refactor, or an architecture audit, use code-review.

**`run.py`**（確定性部分寫成腳本，SKILL.md 只寫判斷）：
1. 範圍：`--uncommitted`；多 session 髒樹時由 wrap-up 傳入本 session 檔案清單 → 以 prompt 限定只審這些檔（codex review 無 path 參數）。
2. `gitleaks detect --no-git --source <files>`（`which gitleaks` 沒有就跳過並在 REVIEW.md 註記 `secret_scan: skipped`）。
3. 第一輪 `codex exec review --uncommitted --json` → 從 JSONL 取 `thread_id`、最後 `agent_message`。
4. 命名：`python3 bin/session-adapter.py show` 取原 session 標題與 ID → `session-adapter.py rename --host codex --session <thread_id> 'quick-review ← <title> (<id8>)'`（無標題時 `quick-review ← <id8>`）。已實測可用。
5. 第二輪 `codex exec resume <thread_id> "<commons.md + docs/review-standard.md>；只報上一輪沒有的；同格式" --output-schema <schema.json>`。
6. 合併兩輪 → `REVIEW.md`：沿用 code-review 的 frontmatter，加 `engine: codex`、`codex_thread: <id>`、`secret_scan:`；body 分「General findings（第一輪）」與「Checklist findings（第二輪）」兩區（觀察錨定用）。P0/P1→Critical、P2→Warning、P3→Suggestion。
- **Fallback**：沒有 `codex` 或在 Codex host 上 → spawn 一個 Sonnet（Codex：繼承）reviewer 做第一輪，再 SendMessage commons 做第二輪；REVIEW.md 註記 `engine: agent`。
- 不改 source、不跑 typecheck/test、不派其他 agent。

## 3. `skills/code-review/` 改版

- **description**：改成定案稿（before merging a branch / large refactor，on demand；`tree` mode 保留；指名 quick-review 給例行檢查；保留 Supersedes built-in）。
- **預設範圍**：Phase 0 已經是 `merge-base HEAD origin/main`（[SKILL.md:29](../../agent-skills/dev-skills/skills/code-review/SKILL.md#L29)），不用改，只把「local git diff」的說法拿掉。
- **Phase 1**：context agent 不再找 plan（plan 歸 /align）；改回傳 `has_design_md`、diff 類型（logic／style-only／docs-only／query-touching）。
- **Phase 2 路由**（取代「固定六個」）：

  | agent | 觸發 |
  |---|---|
  | bugs-security | 有邏輯變更（非純文案／樣式／文件） |
  | standards（原 claude-md） | 一律；兩輪：先依專案指令自由審，再 SendMessage commons 補漏 |
  | performance | 動到 query、迴圈、列表 render、API |
  | quality-architecture | 新增檔案／抽象層，或 diff > 300 行；UI 重複套 impeccable `extract` 準則（同意圖 3+ 次才合併、意圖不同保持分開）；有 DESIGN.md 時 UI drift 不報 |
  | git-history | 只在使用者要求時 |

  REVIEW.md 開頭加「派了哪些／跳過哪些／原因」；`--agents a,b` 可強制。
- **Phase 3**：Haiku 0–100 scorer → **每條 finding 一個二元 verifier**（real / not real ＋ 一句理由；Claude: Haiku，Codex: 繼承）。standards 引用條文的 finding 跳過 verifier（改成 orchestrator 直接 grep 條文是否存在）。False-Positive Categories 保留當 verifier 的固定黑名單。Severity 改由 reviewer 給、verifier 只決定去留。
- **刪除** `agents/plan-adherence.md`（內容併入 /align end 的核對規則）；`agents/claude-md.md` → `agents/standards.md`；Output Format 移除 Plan Adherence 節、CLAUDE.md Adherence 改名 Standards。
- Tone Constraints 改為「見 `shared/review/commons.md` ①」。

## 4. `skills/align/`（新）

**description**：Check that what's being built matches what was asked, across the requirement chain transcript → meeting notes → task file → plan (any stage may be missing). `start` before writing/approving a plan; `end` at wrap-up to check the baseline item by item and write unfinished / untested / open questions to TODO.md.

- **找段**：transcript（會議檔的 `資料來源`／`Source`、`<basename>-transcript.*` sidecar——沿用 upload-meeting §4b 的順序）、meeting notes（`docs/meetings/`、task `# Context` 的 mention）、task（`docs/tasks/<slug>.md`）、plan（本 session plan 檔、`docs/plans/`）。缺的段直接跳過。
- **start**：基準 = 最下游存在的段。預設只往回比一段；有疑義才回到 transcript。上游有、下游沒有的每一項 → `AskUserQuestion` 三選一：加進基準／在別的 task（填名稱）／移到 TODO.md。結果寫成 plan 末尾 `## Baseline`（沒有 plan 就寫在 task 檔），每條一行、附來源（段＋原文短引）。
- **end**：逐條核對 `## Baseline`，每條要附證據（測試名、截圖路徑、`file:line`）；沒證據 = 未驗。✗ 的寫進 TODO.md。同時列出 TODO.md 中與本次改動相關、或超過 14 天未動的項目。
- **TODO.md 格式**（不存在就建在 repo 根目錄）：`## 未完成／未驗` · `## 待客戶確認` · `## 需要人手操作`；每條 `- [ ] <事項>（來源：<段／檔>，<日期>）`；做完就刪（沿用 sparktoy、meetmeoffline 既有慣例）。

## 5. 其他 skill（各一段，最小改動）

| 檔 | 改動 |
|---|---|
| `wrap-up/full.md` §3 | `/code-review` → `/quick-review`；之後 `/align end`。Fix/Defer 流程不變；Defer → TODO.md（非僅 report）。§4 的「有 TODO.md 才 update-docs」改為「TODO.md 已由 /align end 寫好」 |
| `wrap-up/quick.md` | 加一列 `/quick-review`（在 Report 前）：只有 Critical 跳 popup（修／延後），其餘進 TODO.md；Guardrails 改「Never run `/code-review`（用 quick-review）」；closing message 的「跳過」移除 code review；加 `/align end`（不問問題，✗ 直接寫 TODO.md） |
| `wrap-up/SKILL.md` | description 流程字串 code-review → quick-review |
| `sync` Phase 5 | ready report 加一行：TODO.md 超過 14 天未動的項目數＋前 3 條 |
| `create-tasks` §7／§9 | plan 每條 commitment 必須是 LINK／DRAFT／SKIP（附理由）／TODO 之一；§9 執行後未核准或未執行的項目寫進 TODO.md（防 ZIP 那種半批遺失） |
| `report` Issue Resolution | `# Unsolved Issues` 待辦部分改指向 TODO.md（報告留一行計數＋連結） |
| `update-docs` | TODO.md 那條改成「由 /align end 負責，這裡不重複寫」 |
| `improve` Ask scope | 新增選項 **Review commons** → 追加到 `shared/review/commons.md` ④ |
| `README.md` | skill 表加 quick-review、align；改 code-review、wrap-up 列；流程圖；`<skill-name>` 安裝清單（AGENTS.md 規則 2，同 commit） |
| `~/.claude/CLAUDE.md` | 一行：「除非使用者要求分段，做完整條；未完成、未驗、待問的事進 TODO.md（/align end）」；背景 agent 第 9 條補「核對用 /align」 |

## 延後（追蹤位置）

- PR/CI tier（`pr-review` ＋ yml）→ TODO：dev-skills `TODO.md`「未完成」節。
- `docs/site` 的 code-review 描述 → 同上。
- design skill 那側（brief.md 只放設計素材、驗收流程進 plan、⑤ Flow 列用 /align start、[design/SKILL.md:28](../../agent-skills/dev-skills/skills/design/SKILL.md#L28) 的邊界句）→ 由 session `ebd15042` 處理；我請使用者轉貼訊息。
- `/sync-org-forks`：合併回 main 後跑。

## 執行方式

可平行的檔案群（實作時依規則先問是否派 agent）：A＝commons＋quick-review；B＝code-review 改版；C＝align；D＝第 5 節小改＋README。B、D 依賴 A 的 commons 路徑（先建 A 的檔案骨架）。

## Verification

1. **quick-review**：在 scratchpad `crtest`（hard-coded key＋SQL 拼接）跑 `run.py` → REVIEW.md 兩區都有（SQL 在 General、key 在 Checklist）、`codex_thread` 有值、thread 名稱為 `quick-review ← … (d9a99d25)`；無 gitleaks 時 `secret_scan: skipped`；`PATH` 拿掉 codex 時走 fallback。
2. **code-review**：在 `review-align` 分支對 main 跑 → 開頭列出派／跳過；純 md 改動時 bugs-security、performance 被跳過；verifier 回二元結果。
3. **/align start 回歸**：sparktoy 10/07 會議 → `_plan-2026-10-07-上架與圖片任務重整.md` → Notion task 鏈，應標出 I02「匯入預覽逐商品上傳圖片包」為「上游有、下游沒有」。
4. **/align end**：用一份 3 條 baseline 的假 plan（1 條有測試、1 條無證據、1 條待問）→ TODO.md 三節各出現對應項。
5. `grep -rn 'plan-adherence\|claude-md.md' skills/` 無殘留；`grep -n 'quick-review\|align' README.md` 表格與安裝清單都有。


# Review 重設計：quick-review、code-review 路由、/align、TODO.md

## 摘要

```
現在 ❌                                         改後 ✓
wrap-up ─► /code-review                         wrap-up ─► quick-review（每次）
           6 agents + Haiku scorer × N                     ① codex review（自由審，不給清單）
           9/24 後沒跑過，跳過 16–17 次                     ② resume 同 thread + commons（只報新的）
                                                           + gitleaks（有裝才跑）→ REVIEW.md
                                                ─► /align end ─► 基準清單逐條核對 ─► TODO.md
merge 前 ─► （沒有）                             merge 前 ─► code-review（隨 diff 派 agent + 二元 verifier）
需求漏掉／做歪 ─► 人看畫面才發現                  plan 前 ─► /align start（逐段往回比）
```

| 項目 | 狀態 |
|---|---|
| `shared/review/commons.md` | ✓ 寫好 |
| `quick-review`（新） | ✓ 實測（見 Verification） |
| `code-review` 改版 | ⚠️ 只讀過、沒實跑 |
| `/align`（新） | `end` ✓ 手動照做一次；`start` ⚠️ 沒跑 |
| wrap-up／sync／create-tasks／report／update-docs／improve／README | ⚠️ 只改文字 |
| 全域 `~/.claude/CLAUDE.md` | ✓ 加「做完整條、未完成進 TODO.md」 |

# Description

- 起點：`/find-session code review` → 找回 9/24 三層 review 討論（session `38a9fd43`，[transcript](2026-09-24-review-tiers-design-and-survey-transcript.md) 在 `~/agent-skills/docs/reports/`）與 10/28 工作流程回顧（`~/agent-skills/docs/reports/2026-10-28-dev-skills工作流程回顧-事實觀察與分析.md` §4、§5、§8）。
- 問題：`/code-review` 固定 6 agent＋每條 finding 一個 Haiku scorer，成本高而被跳過；6 個 agent 也不涵蓋實際發生的落差（利潤率做歪、ZIP 漏掉、10/28「fix all mentioned in 10/22 meetings」）。
- 目標：每次都能跑的輕量 review、merge 前的深度 review、需求鏈對齊，以及由核對產生（不是 agent 自報）的 TODO.md。

## 討論中定案（使用者原話）

| 主題 | 使用者 | 結果 |
|---|---|---|
| quick 引擎 | 「Use codex review.」 | `codex review`（跨模型） |
| 需求來源 | 「From plan adherence, then meetings decision because plan missed out something」；「transcript (raw truth) -> meeting notes -> task file -> plan sometime some stage may be missing」 | 新 skill `/align` |
| 做完整條 | 「Should do everything from start to end unless is specified by the user … Any undone task, test or questions should go to TODO.md」 | 全域 CLAUDE.md＋`/align end` |
| 安全 | 「Every run require security scan, is this included in codex?」 | 拆出 codex 內建 prompt：security 只是四個標準之一、沒清單 → commons ③＋gitleaks |
| 錨定 | 「我擔心我們有明確寫的話然後他就只會照著這個做不會去檢查其他的」→「可不可以先叫他自己review在send message給他補強檢查」 | 兩輪：自由審 → resume 給清單 |
| quick 不用 impeccable | 「Quick wrap up no need impeccable.」 | 移除 |
| 名稱 | 「use quick-review and code-review, but state how is it used in description」 | 不改名，description 寫使用場景 |
| thread 命名 | 「we already have rename session, the name should recognize somehow with the original session」 | `quick-review ← <原 session 標題> (<id8>)` |
| commons | 「full + include new rules from improve run」 | 全量＋`## Added by /improve` 區 |
| 其他 | code-review 預設 merge-base main、commons 放 `shared/review/`、PR tier 延後、gitleaks 有裝才跑、design 那側由它自己處理、TODO 規則進全域 CLAUDE.md | — |
| TODO.md 格式 | 「TODO.md 目前的格式只是 temp，我們之後來討論」 | 暫定，已列進 TODO.md |

# Changes Made

- **共用 review 標準** — 下限不是範圍；①註解規則（只評 `+/-` 行、宣告式、四級 severity）②基本標準（八條，取自使用者 CLAUDE.md 反覆糾正的規則）③安全清單（七條）④ `/improve` 追加區；專案可加 `docs/review-standard.md`。
  `shared/review/commons.md`
- **quick-review（新）** — `run.py`（stdlib）：gitleaks（工作檔＋staged blob、只報改到的行）→ round 1 `codex exec review --uncommitted|--base <ref> --json`（`--files` 時改用 prompt-only，因為 `--uncommitted` 不收 prompt）→ 用 `session-adapter.py` 把 Codex thread 命名 → round 2 `codex exec resume <thread> "<commons + 專案標準>；只報新的"` → 合併寫 REVIEW.md（General／Checklist 兩區、`session:`、`engine`、`codex_thread`、`secret_scan`）。他人的 REVIEW.md 不覆寫，改寫 `REVIEW-<id8>.md`；沒跑完的輪次 → `status: incomplete`（exit 4）；沒 codex 或在 Codex host → exit 3 走 agent fallback（`--print-prompt`、`--from-text`）。
  `skills/quick-review/SKILL.md`、`skills/quick-review/run.py`
- **code-review 改版** — description 改為「merge 前／大重構，on demand」；Phase 1 回傳 diff 類型與 `has_design_md`；Phase 2 依 diff 派 agent（bugs-security／standards 一律／performance／quality-architecture／git-history 只在要求時），REVIEW.md 開頭列派與跳過；standards 兩輪（自由審 → SendMessage commons）；Phase 3 改成每條 finding 一個二元 verifier，引用條文的 finding 由 orchestrator grep 驗；quality-architecture 加 impeccable `extract` 準則、有 DESIGN.md 時不報 UI drift；刪 plan-adherence、`claude-md.md` → `standards.md`；frontmatter 加 `session:`。
  `skills/code-review/SKILL.md`、`skills/code-review/agents/*`
- **/align（新）** — 找段（transcript／meeting notes／task／plan，缺的跳過）；`start` 基準＝最下游的段、往回比一段、上游有下游沒有的逐條三選一，寫 `## Baseline`；`end` 逐條附證據（無證據＝未驗）＋原 plan-adherence 的漏做／scope creep／未記錄的 breaking change，✗ 進 TODO.md；`end --quick` 不問問題。
  `skills/align/SKILL.md`
- **其他 skill** — wrap-up Full §3 改 quick-review＋/align end（附 `--files`／`--base` 傳法），Quick 加 quick-review（只有 Critical 跳 popup）與 `/align end --quick`、步驟重編號；sync 列超過 14 天的 TODO；create-tasks 每條 commitment 必須落在 LINK／DRAFT／SKIP（附理由）／TODO，未執行的寫進 TODO.md；report、update-docs 的 TODO.md 改指向 /align；improve 新增「Review commons」範圍；README 表格、流程圖、安裝清單。
  `skills/wrap-up/{full,quick,SKILL,commit}.md`、`skills/{sync,create-tasks,report,update-docs,improve}/SKILL.md`、`README.md`
- **全域規則** — `~/.claude/CLAUDE.md` 加「做完整條再停；未完成、未驗證、待問的事寫進 TODO.md（/align end）」；背景 agent 第 9 條補「用 /align end 核對」。（不在 repo 內）
- **TODO.md（新）** — 本次 `/align end` 的產出，列出未驗項目與延後事項。
  `TODO.md`

實作方式：worktree `../dev-skills-review-align`（分支 `review-align`，因為 main 有其他 session 未 commit 的 README 等改動）；commons 由主 session 先寫，其餘分給四個平行 agent（A quick-review、B code-review、C align、D 其他 skill＋README），整合時主 session 測試與修正。

# Verification

- **codex 內建 review 的 prompt**：從 Codex 0.166 binary 抽出 → security 只是「accuracy, performance, security, or maintainability」之一，無清單；會讀 AGENTS.md。
- **兩輪可行性**（scratchpad 測試 repo：`KEY="sk-live-123"`＋字串拼 SQL）：round 1 只抓到 SQL injection（`[P1]`，還自己跑 SQLite 驗證）、漏掉 key；`codex exec resume <thread>` 給清單後抓到 key（`[P2]`）。
- **run.py 端到端**（新建 `crtest2`，同樣兩個問題）：`Found 2 findings (2 critical…)`；General＝SQL、Checklist＝key；`codex_thread` 有值；`session-adapter.py show` 顯示 thread 名稱 `quick-review ← code-review 精簡化討論 (d9a99d25)`。
- **參數與邊界**：`--base nope` → exit 2「not a valid commit」；`--files a.py` 時另一個檔的 `eval(input())` 不出現；`--files <絕對路徑>` 正確對應；REVIEW.md 的 `session:` 是別人或沒有 → 寫 `REVIEW-d9a99d25.md`；`changed_lines` 只回改到的行（`{1,2,4,5,6}`，未改的第 3 行不在內）。
- **Fallback**：`--from-text r1 r2` → `engine: agent`，round 2 與 round 1 重複的那條被去重；round 檔為空 → `status: incomplete`、exit 4。
- **gitleaks 路徑**（本機沒裝，用假的 `gitleaks` 腳本）：secret 先 `git add` 再從工作檔刪掉 → staged blob 仍被抓到（`secret_scan: found`）；staged PNG 不會讓掃描崩潰。
- **quick-review 自審本分支** 4 次，共找出 18 個 run.py 問題，皆已修（見 Updates）。
- **沒有跑的**：code-review 改版（路由、verifier、standards 兩輪）、`/align start`（sparktoy ZIP 回歸）、真正的 wrap-up Full／Quick 新流程、真的 gitleaks——都列在 `TODO.md`。

# Updates

- **實作期間測試抓到**：`codex exec review --uncommitted` 不能帶 custom prompt（`the argument '--uncommitted' cannot be used with '[PROMPT]'`）→ `--files` 時改用 prompt-only 模式描述範圍。
- **thread 改名失敗**：`session-adapter.py` 子程序找不到 `codex`（nvm PATH）→ 傳入含 nvm 的 env。
- **quick-review 自審修正**（第 1 輪 6 條、第 2 輪 5 條、第 3 輪 3 條、第 4 輪 4 條）：
  - Fixed [Critical] `run.py` — 無條件覆寫他人 REVIEW.md → `session:` 欄位＋`REVIEW-<id8>.md`；未知擁有者也視為他人。
  - Fixed [Critical] `run.py` — round 2 失敗仍報 clean → `status: incomplete`、exit 4；gitleaks error、空的 fallback 輪次同樣算 incomplete。
  - Fixed [Critical] `run.py` — 只掃工作檔，漏掉 staged secret → 也掃 index blob（bytes 讀取，避免 binary 崩潰）。
  - Fixed [Warning] `run.py`／`SKILL.md`／`wrap-up/full.md` — 已 commit 的 session 工作沒被審 → `--base <ref>`，fallback 每次呼叫都帶上。
  - Fixed [Warning] `run.py` — `--files` 只事後過濾 → 範圍寫進 round 1 prompt；`--base`＋`--files` 也包含 untracked。
  - Fixed [Warning] `run.py` — 去重只看 (path, line) → 加上標題；沒位置的 finding 不去重。
  - Fixed [Warning] `run.py` — gitleaks 報到未改的行、index 等於 HEAD 時把舊 secret 當新的 → 只報改到的行，未改的已追蹤檔回空集合。
  - Fixed [Warning] `run.py` — codex 非零退出但有輸出仍當成功 → 要求 exit 0 且有最終訊息。
  - Fixed [Warning] `run.py` — 無效 `--base` 靜默變 skipped → 驗證 ref。
  - Fixed [Warning] `run.py` — 非 ASCII 檔名被 git 跳脫 → `--name-only -z`；symlink 被 resolve 成目標 → 改用字面路徑。
  - Fixed [Warning] `run.py` — 未裝 commons 時 `FileNotFoundError` → 改成警告並用最小安全檢查；SKILL.md 註明需整包安裝。
- **整合時補上**：code-review frontmatter 加 `session:`（讓 quick-review 認得）；`commit.md` 的 Quick 步驟編號；`report/SKILL.md` 的 REVIEW.md 說明（不再是 confidence-scored）。
- **跨 session 回報**：design session（`ebd15042`／`agent-skills-e6`）在真實 wrap-up 用到舊版 run.py，回報已 commit 的工作被丟掉、他人 REVIEW.md 被覆寫——兩者在本分支都已修，已回覆對方。
- **/improve（wrap-up 收尾）**：quick-review 自審反覆出現「失敗／空的步驟被當成 clean」→ 加進 `shared/review/commons.md` 的 `## Added by /improve`（第一條）；全域 CLAUDE.md 背景 agent 第 12 條：寫外部 CLI 呼叫時 brief 貼已驗證指令。
- **子 agent 自行決定、與計畫不同的地方**：
  - `/align` 寫進既有 TODO.md 時沿用其結構（使用者選擇保留）。
  - code-review 無法對 live 來源確認的 DB schema finding 由「上限 25」改為直接丟掉。
  - code-review 的 context agent 會掃 diff 片段來分類。
  - Baseline 用 B1/B2 編號，並有 `### Excluded` 小節。
- **PR 收尾** _(2026-11-11)_：
  - PR #2 一開始帶進 4 個其他 session 未推的 design commit（分支從本地 main 切出）→ 用 `git rebase --onto origin/main 279c746` 只留本 session 的 2 個 commit，`--force-with-lease` 推回；README 安裝清單衝突只加 `align`、`quick-review`。
  - design 經 PR #1 先合進 main → PR #2 衝突；把 `origin/main` merge 進 `review-align`（不再 force-push）：安裝清單同時保留 `design`、`align`、`quick-review`；`design/SKILL.md` 的邊界句改指 wrap-up 的 `/quick-review`。PR #2 已合併（`7900b5c`），worktree 與 `review-align` 分支（本地＋遠端）已刪。
  - 安裝：plugin cache 還是 11/3 的 0.1.0（沒有 quick-review、align），自動同步 hook 只鏡像主 checkout 的編輯 → 版本升到 0.2.0，讓 `/plugin update` 抓得到。
  - `/sync-org-forks` 已檢查（unilife 落後 106、dropout 落後 89），使用者選擇先不同步。
  - /improve：`wrap-up/commit.md` 既有「推送前若含他人 commit 要先問」那條，加上優先選項「把本 session 的 commit rebase 到 `origin/<base>`」。

# Result

- 每次 wrap-up 都會跑的 `quick-review`：一次 codex review＋一次 resume，跨模型、帶安全清單、不錨定；在測試 repo 抓到兩個植入問題，也在本分支自審抓到 18 個真實 bug。
- `code-review` 改成 merge 前用、依 diff 派 agent；`/align` 把 transcript → meeting notes → task → plan 的需求鏈接到 TODO.md。
- 經 PR #2 合併進 main（`7900b5c`），plugin 版本升到 0.2.0；org forks 尚未同步。
- 對其他程式的影響：REVIEW.md 格式改變（無 `Confidence:`、新增 `session:`／`engine`／`status: incomplete`）；wrap-up Quick 現在會跑 review。

# Unsolved Issues

- 待辦細項見 [`TODO.md`](../../TODO.md)（未驗 4 項、延後 3 項、待確認 2 項、人手操作 2 項）。
