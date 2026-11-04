---
session: 2026-11-04-design與impeccable整合實作 (ebd15042-bc5c-4573-bc52-64f2a95c9c85), 2026-11-03-design-skill與impeccable整合規劃 (24de07ec-8599-4b78-b44c-a4b61132ebdd)
---

# Plan

# design × impeccable 整合

## 摘要

```
現在 ❌                                          改後 ✓
design 只有一種流程：整頁方向 ②→⑥ → ⑦ 收斂      三種模式（① 判斷）
  實際上多數 session 風格已定，                    ├ 方向模式：整頁 8 卡 → 校準 → 平行 → 審 → 展示（原 ②–⑥）
  反覆來回都在「單一區塊」與「統一元件」            ├ 區塊模式：同風格、單區塊 3–4 案靜態並排 A–D → 選 → 移植進 code
impeccable 只有 hook 在跑（detect）               └ 統一模式：extract → document（DESIGN.md）
  bolder/adapt/extract/overdrive… 從沒被叫         選定後：使用者一句話 → 對應 impeccable 指令，直接改 code
  live/generate 要 server、慢                     design 永不走 impeccable new-work / live / generate（慢的部分）
```

| 規則 | 落在哪 |
|---|---|
| ① impeccable 較好 → design 直接呼叫 | detect、critique、bolder／quieter／distill／layout／typeset／colorize／animate／clarify／adapt／optimize／overdrive（一頁一個高峰）、extract、document、polish、harden |
| ② design 較好 → 吸收 impeccable 說得更清楚的地方 | generate → 區塊模式靜態頁（借它的方向詞→動作對照）；overdrive「先提 2–3 方向」→ 用區塊選項頁當提案；critique「detector 會錨定判斷」→ 審查者先判再看 detect |

| 審查 | 誰負責 |
|---|---|
| 專案專屬：流程、品牌、高峰時刻、版本差異度 | design `review-checklist.md`（刪掉通用列） |
| 通用・機械：對比、禁用 pattern、間距字級 | `impeccable detect`，每版桌機＋390px |
| 通用・判斷：Nielsen、層級、認知負荷 | `impeccable critique`，只跑使用者傾向的那一版 |
| 程式碼 | `/code-review`（另一個 session d9a99d25 正在重設計；已同步分工：驗收階段重用 brief.md 流程＋detect＋DESIGN.md） |

## Context

使用者發現 impeccable 很好用，但 live／decision page 要開 server 很慢；`design` skill 應該與 impeccable 搭配——補它不足、取代它慢的部分，而不是取代整個 impeccable。回看 3 個 UI session（官網 V1 改版、App 改版原型、UI Library 統一）：沒有一次叫過 impeccable 指令；來回多半是「同風格下單一區塊多方案」「已選區塊調整」「統一成元件」，而 design 目前只寫了整頁方向流程。

## 改動

### 1. `skills/design/SKILL.md`（最小幅度編輯，不重寫）

- **開頭段**：加一句分工——design 負責選方向、多版本、靜態 HTML；細修與系統化交給 impeccable 指令；**不走** impeccable 的 new-work、`live`、`generate`、`serve-question`（要 server，慢）。impeccable 沒安裝時照 design 自己做並說一聲。
- **① 收集**：
  - 有 PRODUCT.md／DESIGN.md 就讀；產品事實放 PRODUCT.md，`brief.md` 只留本輪驗收流程與品牌規則。
  - 判斷模式：已有視覺權威（現有站、DESIGN.md）＋只改部分 → 區塊模式；要求統一／元件庫 → 統一模式；其他 → 方向模式。
- **② 方向頁**：刪掉 `~/.claude/design-taste.json` 那句（從未寫入；改由 DESIGN.md 承接）。
- **③／④**：subagent brief 指向 impeccable 的 `craft-floor.md`（品質底線、禁用清單）。
- **⑤ 審查**改為：A 審查者先依 checklist 判（不看 detect）→ B 每版跑 `impeccable detect`（桌機＋`--viewport 390x844`），兩者合併 → 修 fail。critique 移到選定後。
- **新增「區塊模式」段**（短）：同風格、單區塊 3–4 案放同一靜態頁 A–D；頁面**引入專案真實 CSS／tokens**，不模仿；方向詞借 generate 的對照（bolder／quieter／…）；需要招牌效果時，選項頁即 overdrive 的提案步驟，選定後再照 overdrive 實作。選定 → 移植進 code。
- **⑦ 收斂**改為：
  - 選定版先跑 `critique`。
  - 之後依 `references/impeccable.md` 的對照表，把使用者的反應轉成指令，**直接改 code**；git 當 rollback；給使用者一個**不 auto-reload 的 port**（先 `lsof` 看有沒有在跑的）。
  - 收尾 `polish` → `harden` → `document`（寫 DESIGN.md）。
  - 刪掉 taste 檔 append；保留「把使用者確認的新風格補進 styles/」。
- **新增「統一模式」一行**：`extract` → `document`。
- **結尾一句邊界**：design 審 rendered 結果；程式碼品質留給 wrap-up 的 `/code-review`。

### 2. 新檔 `skills/design/references/impeccable.md`

- 怎麼呼叫：用 Skill `impeccable:impeccable` 帶 `<command> <target>`；`detect` 直接跑 impeccable skill 目錄下的 `scripts/impeccable detect <file|url>`（Claude／Codex 安裝路徑不同，從已安裝的 skill 目錄解析，不寫死版本）。
- 對照表（使用者說法 → 指令 → 該指令的關鍵規則一行），例：
  - 「太平、像別的頁的弱版」→ bolder（只用系統已有的招式，只動目標）
  - 「空空的／太擠／不平衡」→ layout
  - 「太吵、不要金漸層／框／icon」→ quieter／distill
  - 「要呼吸感、掀起、搖晃、stack 感」→ animate
  - 「顏色不搭／別變紫」→ colorize（保留品牌色）
  - 「這句很廢／這行怪」→ clarify
  - 「手機要重新想，不是縮小」→ adapt
  - 「卡頓」→ optimize
  - 「要沒人想過網頁能做的效果」→ overdrive（一頁一個；先提案）
  - 「統一成元件／規範」→ extract → document
  - 「快好了」→ polish → harden
- 注意：方向還沒定時說「更大膽」= 換一批方向，不是 bolder 指令；extract 沒有設計系統時會先問放哪。

### 3. `skills/design/references/review-checklist.md`

- 只留 Flow、Brand、Peak moment、Distinctness 四列。
- Usability／Accessibility／Visual 換成一行：通用品質由 detect（每版）與 critique（選定版）負責。

### 4. `description`（frontmatter）

- 加區塊／統一模式觸發詞：「這個區塊多做幾個方案」「統一元件」「UI library」。
- 維持「not for system/API design」。

## 協調

- `4375beb0`（design 原 session）此刻正在 wrap-up／improve 同一個 SKILL.md，工作區還有一行未 commit 的 Artifact 政策改動。**等它結束再動**；動手前重讀現檔、`git status`／`find skills/design -mmin -15` 確認沒人在寫。
- `d9a99d25`（code-review 重設計）已收到分工，對齊 brief.md 驗收流程格式這件事等兩邊定案再改。

## 驗證

1. `grep` 每項改動的標記：
   - `impeccable.md` 連結
   - `detect --viewport`
   - `區塊模式`／`Block mode`
   - 確認已無 `design-taste.json`
2. 確認 impeccable 指令能跑：
   - `impeccable detect <某個 docs/design/*.html>`（Claude 與 Codex 兩邊的安裝路徑）
   - Skill `impeccable:impeccable bolder` 的路由不會掉進 new-work
3. 重新安裝 dev-skills 到 Claude Code 與 Codex，diff 快取與工作樹一致。
4. （可選）拿一個真實區塊試跑區塊模式，例如 meetmeoffline 的信封。
5. 完成後問 commit（獨立 commit，可單獨 revert），再跑 `/sync-org-forks`。


# design 與 impeccable 整合實作

# Description

- 照 `~/agent-skills/docs/reports/2026-11-03-design-skill與impeccable整合規劃.md` 文末核可計劃實作：design 分三種模式、review 三層、新 `references/impeccable.md` 對照表、刪品味檔。
- 圖像化的完整演進報告（10/14 → 11/04、為什麼最後長這樣）：[2026-11-04-design-impeccable-整合報告.html](2026-11-04-design-impeccable-整合報告.html)，樣式沿用 `docs/site/styles.css`。

```
現在 ❌                                          改後 ✓
design 只有整頁方向 ②→⑦                          ① 判斷：方向／區塊／統一 三種模式
impeccable 只有 hook（detect）在跑                 選定後：使用者一句話 → impeccable 指令直接改 code
review：一個審查者 6 列全包                       checklist（專案專屬＋可用性基本）→ detect（機械）→ critique（選定版）
品味檔 ~/.claude/design-taste.json（從沒寫過）     刪掉，改由 document 寫 DESIGN.md
```

# Changes Made

- **分工句（開頭）**：design 選方向／多版本／靜態 HTML；選定後細修交給 impeccable；不走 new-work、`live`、`generate`、`serve-question`（要 server、慢）；impeccable 沒裝就自己做並說一聲。
  `skills/design/SKILL.md`
- **① 收集**：讀 `PRODUCT.md`／`DESIGN.md`（缺 PRODUCT.md 時提議 `init`）；產品事實放 PRODUCT.md，`brief.md` 只留本輪驗收流程與品牌規則；判斷模式（已有視覺權威＋只改部分 → 區塊；統一／元件庫 → 統一；其他 → 方向）。
- **② ⑦**：刪 `~/.claude/design-taste.json` 讀寫（從未被寫過）。
- **③／④**：校準要過 impeccable `reference/craft-floor.md`，絕對路徑交給每個 builder；與 brief／style guide 衝突時後者優先。
- **⑤ 審查**：fresh reviewer 先依 checklist 判（flow → usability basics → brand → peak moment → distinctness），不看 detector 輸出；再跑 `detect` 桌機＋`--viewport 390x844`；`critique` 移到 ⑦。
- **⑦ 收斂**：選定版跑 `critique` → 反應對照成指令直接改 code（git rollback；專案自己的 server、固定 port、不 auto-reload；沒 code 就給 HTML 路徑）→ `polish` → `harden` → `document`。
- **Block mode／System mode** 兩段新文字；結尾邊界句（程式碼品質留給 wrap-up 的 code review）；description 加觸發詞「這個區塊多做幾個方案」「統一元件」「UI library」。
- **新檔** `skills/design/references/impeccable.md`：呼叫方式、detect 路徑解析（Claude／Codex、取最新版）、URL 掃描、stderr、exit code、使用者說法 → 指令 → 關鍵規則 13 列。
- `skills/design/references/review-checklist.md`：6 列 → Flow／Usability basics／Brand／Peak moment／Distinctness；通用品質指向 detect／critique。
- `README.md`：design 列改寫成三模式＋禁用的 impeccable 指令。

Commit：`279c746`（初版，已 push 到 PR #1 `feat/design-style-vocabulary`）；review 修正與 README 在本次 wrap-up commit。

# Verification

- `grep`：`impeccable.md` 連結 3 處、`viewport 390x844`、`Block mode` 皆在；`design-taste` 0 筆。
- `impeccable detect --quiet --viewport 390x844 file:///…/docs/site/index.html` → 「95 anti-patterns found. 45 advisory notes」，免 server（規劃時標為未驗證）。直接掃檔案（非 URL）同頁只有 28 條，所以 skill 寫成一律 URL 掃描。
- Claude（`~/.claude/plugins/cache/impeccable/…/4.3.1`）與 Codex（`~/.codex/plugins/cache/impeccable/…/4.3.1`）兩個 detect 對 `docs/site/v2/index.html` 都跑出結果。
- `bolder` 不會掉進 new-work：讀 `reference/bolder.md` 開頭（「This command refines a surface whose world already shipped」）確認；**未實際呼叫**。
- 安裝：Claude 快取 `diff` 與 repo 一致；Codex `~/.codex/skills/design` 是連到 repo 的 symlink。
- 未做：新版 SKILL 在真實專案實跑；區塊模式試跑。

# Updates

- 第 8 行 Artifact 政策是 session 8b6cac38 的未 commit 改動；問了 4375beb0（非作者，拒代 commit），使用者讓 8b6cac38 自己 commit 成 `256df2a` 後才動手。依使用者指示疊在 PR #1 上。
- `/sync-org-forks` 延後：fork 從 `origin/main` 同步，本次改動要等 PR #1 merge。
- 進度簡報 HTML 被說「做得不好」→ 改成報告 HTML；再依「要詳細點」「把前面幾份討論的topic也包含進來…要可以看出為什麼最後會長這樣」「要用site的design style」「要圖像化」四輪改成現在的整合報告。
- Code review 用新的 quick-review（`dev-skills-review-align` worktree，codex 未安裝 → fallback：一個 Sonnet reviewer 兩輪）。10 條全修，複審全部 resolved、無新問題：
  - Fixed [Warning] `skills/design/references/review-checklist.md:3` — 可用性／無障礙檢查被移除、展示的版本都沒檢查 → 加回 Usability basics 列，⑤ 順序加入。
  - Fixed [Warning] `skills/design/SKILL.md:18` — craft-floor 路徑 builder 解析不到、與 style guide 誰優先未寫 → 寫明解析絕對路徑，brief／guide 優先。
  - Fixed [Warning] `skills/design/SKILL.md:24` — 區塊模式引入真實 CSS 在 Artifact 發布時失效 → 發布時用 `files` 傳或 inline。
  - Fixed [Suggestion] `skills/design/SKILL.md:20` — `impeccable detect` 寫成裸指令、不在 PATH → 指向解析方式；`impeccable.md` 補 exit code。
  - Fixed [Suggestion] `skills/design/SKILL.md:24` — 區塊選項用指令動詞命名，違反「公認名稱」→ A–D＋一行說明，動詞只當生成方向。
  - Fixed [Suggestion] `skills/design/SKILL.md:26` — 統一模式沒有審查、互動停點沒寫 → 補上 extract／document 會問的事與 grep 舊 pattern 確認遷移。
  - Fixed [Suggestion] `skills/design/SKILL.md:16` — 沒有東西建立 PRODUCT.md → 缺時提議 `init`。
  - Fixed [Suggestion] `skills/design/SKILL.md:22` — ⑦ port 說法模糊 → 專案自己的 server；沒 code 給檔案路徑。
  - Fixed [Suggestion] `skills/design/references/impeccable.md:31` — 「design ②」標記不存在 → 「design step 2, Direction page」。
  - Fixed [Suggestion] `README.md:54` — 禁用指令列得比 SKILL.md 少 → 四個都列。

# Result

- design 現在分三種模式，選定後的細修與系統化交給 impeccable 指令，慢的 live／generate／decision page 不再使用。
- 圖像化報告：`/Users/unilife/agent-skills/dev-skills/docs/reports/2026-11-04-design-impeccable-整合報告.html`。

# Unsolved Issues

- [Conflict] `skills/design/SKILL.md:16` — code-review 重設計（d9a99d25，`~/.claude/plans/reactive-pondering-sketch.md` §延後）要 brief.md 只放設計素材、驗收流程進 plan、⑤ Flow 列用 `/align start`；本次仍寫「brief.md 只留本輪驗收流程與品牌規則」（deferred because: `/align` 尚未落地，等兩邊定案）。
- PR #1 merge 後跑 `/sync-org-forks`（兩個 fork 落後 main 10+ commit）。
- 區塊模式選項頁檔名慣例；真實區塊試跑（例：meetmeoffline 信封）。
- quick-review `run.py --from-text` 會丟掉已 commit 檔案上的 findings（只看 uncommitted），本次手寫 `REVIEW-design-impeccable.md`。
- 規劃報告在 `~/agent-skills/docs/reports/`（非 git repo），是否搬進 dev-skills 待決定。
