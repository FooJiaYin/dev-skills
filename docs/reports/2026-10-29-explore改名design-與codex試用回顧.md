# explore 改名為 design，以及 Codex 第一次試用的回顧

## 摘要

```
現在 ❌ skills/explore（13 行）                 改後 ✓ skills/design（六步）
先問一題定軸 → 只做差異區塊 → 截圖 → 預覽 → 合併   ① 收齊素材 → brief.md
                                               ② 方向頁 HTML：2–4 大類別 → 8 張卡（公認風格名、參考網站）
                                               ③ 每版一個 subagent，互不看
                                               ④ fresh reviewer 依 review-checklist.md 審，附截圖
                                               ⑤ 同一頁隨機順序＋現況還原
                                               ⑥ 合併成新版、_archive/、品味檔
```

| 項目 | 狀態 |
|---|---|
| `skills/explore` → `skills/design`（`git mv`），name、description 改寫 | ✓ |
| `references/review-checklist.md`（流程 → 體驗 → 無障礙 → 品牌 → 視覺） | ✓ |
| Claude Code、Codex 重新安裝 | ✓（Codex 另加 `~/.codex/skills/design` 連結） |
| `catalog.json`、`build-catalog.mjs`、`taste.mjs`、README 一列 | ✗ 延後 |

背景研究見 `~/agent-skills/docs/reports/2026-10-23-design-variants-decline-survey.md`、`2026-10-23-ui-design-sessions-analysis.md`；計畫見 `~/.claude/plans/optimized-dazzling-river.md`。

## 為什麼

使用者常請 AI 做三個視覺版本，結果第一版最好、後面越來越平庸。survey 與過去 session 分析的結論：留下來的版本都錨定在真實素材（既有網站、DESIGN.md、報名表），被砍的都是自創主題；抱怨多半是內容太薄、沒用到既有素材、只換皮。所以流程把「先收素材、先定方向、各版互不看、獨立審查」放在前面。

## Codex 第一次試用（2026-10-29，小聰頭／聰頭AI，session 01a1859c、01a1863c）

```
叫 design → 8 張方向卡（CSS 草圖）→「直接給我html」→「超爛，做精緻一點」
→ 改成 Figma／Canva／CapCut 三版完整靜態畫面 → 留 2、3，加玻璃、極簡
→「不是很符合…不要每個都長差不多 參考我給你的圖片」
→ 先列每個風格的 style guide（字體／border／radius／spacing／shadow／佈局）
→ 加 Material → 5 版 →「這才是我要的嘛」→ 水晶漸層 → 命名 →「不要那麼文藝」→「不要那麼多廢話」→ flyer 部署
```

| 卡住的地方 | 原因（SKILL 這版缺的） |
|---|---|
| Codex 沒有 Artifact，改用 ChatGPT page，被說「直接給我html」 | SKILL 寫死 Artifact |
| 第一頁「超爛」 | 方向卡是 CSS 小線框；當初討論的 ③ 試作校準被刪掉 |
| AI 想不出風格名，使用者自己說出 dark glassmorphism、Material，還自己找圖 | 當初討論的「詞彙層」（感覺詞 → 公認風格名＋tokens＋真實截圖）與參考庫延後 |
| 玻璃與極簡長一樣（同一個三欄版面換色） | 當初討論的解讀卡／Style Tile（各軸取值）縮成一行；補上 style guide 表後才對 |
| 文藝命名、對客文案太多被退 | 只要求方向卡用公認名稱；沒區分給客戶看的頁面與給使用者的比較表 |
| 品味檔從沒被寫 | `~/.claude/design-taste.json` Codex 也不一定寫得到 |

使用者明確表示：**不希望未來要自己給圖**——給圖是因為 AI 做不好，AI 應該自己找風格名和參考圖。

## Unsolved Issues

- 補回：詞彙層＋參考庫（UI UX Pro Max 起步，StyleKit 等待查證）、每版 style guide 表與並排比較、試作校準、Artifact 不可用時的 HTML 路徑、對客頁面極簡、公認風格名。
- Codex session 存進 `skills/design/references/styles/` 的 6 張圖疑似第三方作品（Dribbble 類），dev-skills 會同步到 org fork；已依使用者指示另一個 commit 收進來，之後再決定是否改成只放連結＋tokens。
- `SKILL.md` 的「Visual reference library」段落（Codex 加的）與 `styles/` 同一個 commit，下一步重寫時處理。
- `pdftoppm` 缺（`brew install poppler`）未處理。

# Suggested Doc Updates

- `README.md`：skills 表加一列 `design`（planning／design 類），說明「視覺／UI 設計：HTML 方向頁 → 平行預覽 → 審查 → 合併」。README 目前有其他 session 未 commit 的修改，之後以最小 Edit 加入。
