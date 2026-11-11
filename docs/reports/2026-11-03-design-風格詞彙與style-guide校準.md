# design：AI 自己找風格名與參考圖、每版 style guide、試作校準

## 摘要

```
現在 ❌（10/29 版）                              改後 ✓
① 收素材                                         ① 收素材 → docs/design/brief.md
② 8 張卡：風格名＋一個參考網站＋CSS 小線框          ② 方向頁：AI 從參考庫挑公認風格名，自己截真實網站圖
   （AI 想不出名字，使用者自己找圖）                   每個風格：名稱＋圖＋一行為什麼適合 → 使用者挑
                                                     挑中的才寫 style guide（含構圖），並排比較表放對話
③ 平行預覽                                        ③ 試作校準：一張精緻主畫面，過了品質門檻才做其他版
④ 審查  ⑤ 同一 Artifact  ⑥ 合併                    ④ 平行做（同範圍） ⑤ 審查 ⑥ 給客戶看的頁面極簡 A/B/C ⑦ 合併＋新風格回寫參考庫
```

| 檔案 | 改了什麼 |
|---|---|
| `skills/design/SKILL.md` | 六步 → 七步（加試作校準）；HTML 預設存本機；風格詞彙由 AI 找；對客頁面極簡；新風格回寫原始 repo |
| `references/style-guide.md`（新） | 每版 style guide 範本（名稱、參考、tokens 含構圖、套到產品、常見失敗）＋並排比較表；「同版面換材質＝同一版」 |
| `references/styles/ui-ux-pro-max-styles.csv`（新） | UI UX Pro Max 88 種風格，鎖 commit `28b3b8d`，MIT |
| `references/styles/THIRD-PARTY-NOTICES.md`（新） | 上述授權全文 |
| `references/styles/*.md`、`manifest.json`、`index.md` | 移除專案資訊（AI 對話、分鏡、模板、session id）；三份 guide 補構圖列與 CSV 別名；index 補 CSV 使用規則 |
| `references/review-checklist.md` | 「差異」改指向 style-guide 的規則 |
| `README.md` | Dev flow 表加 `design` 一列；install 清單加 `design` |

## 為什麼

10/29 Codex 第一次用 design（聰頭AI 提案）的卡點，都是 10/23 討論過、但第一版 SKILL 沒寫進去的：

| 討論過 | 第一版 | 當時的卡點 |
|---|---|---|
| 詞彙層：感覺詞 → 公認風格名＋tokens＋真實截圖 | 只有「公認風格名＋一個參考網站」 | AI 想不出名字；使用者自己說出 dark glassmorphism、Material，還自己找圖 |
| 解讀卡／Style Tile：各軸取值 | 縮成一行 | 玻璃與極簡同一個三欄版面換色；補了 style guide 表才「這才是我要的嘛」 |
| 試作校準 | 刪掉 | 第一頁線框草圖被說「超爛」 |
| 參考庫 | 延後 | 沒有詞彙來源 |

使用者的原則：**給圖是因為 AI 做不好；以後 AI 自己找風格名字和圖**。另一條：**reference 裡不要有跟專案有關的資訊，只記錄 style**。

## 決定與偏離

- **不做 `catalog.json`／`build-catalog.mjs`／`taste.mjs`**（原 plan）：`styles/index.md`＋guide＋CSV 已夠用；CSV 直接收錄、不轉格式。品味檔仍寫 `~/.claude/design-taste.json`，Codex 是否寫得到未驗。
- **風格名保留 Material Design、Light minimalist**（review W1/W2 建議改成 CSV 名稱）：使用者要「就叫這個風格的名字」；CSV 名稱改列別名。
- **保留「2–4 大類別」**（review S4 建議刪）：是使用者定的篩選方式。
- **Artifact 段落**：本 commit 的首段是「HTML 存在 `docs/design/`，有 Artifact 工具就 publish，否則給路徑」。另一個 session（8b6cac38，10/30）在工作區把它改成「預設給本機路徑，只有 Remote Control 或使用者要求才 publish」，對齊使用者的新全域規則；那段未隨本 commit 提交，留給該 session。

## 驗證

- `/verify` 依使用者指示略過（skill 文字沒有測試計畫）。實際做過的檢查：
  - 所有相對連結解析成功（腳本掃 SKILL.md、style-guide.md、review-checklist.md、styles/index.md，0 broken）。
  - CSV 與上游 `src/ui-ux-pro-max/data/styles.csv`@`28b3b8d` sha256 相同（reviewer 實抓比對）；授權文字與上游 LICENSE `diff` 相同。
  - `references/` 內 grep `AI|分鏡|對話|模板|作品|01a18` 無結果；`manifest.json` 可解析。
  - Claude Code、Codex 重新安裝後，兩邊快取的 `design` 與工作樹一致（review 修正前那次；修正後需再裝一次）。
- 未驗：新版 SKILL 尚未在真實專案跑過。

# Updates

Code review（單一 reviewer，只看 design 範圍）：1 Critical、8 Warning、4 Suggestion → 修 11 項、3 項依使用者決定不改；複審 clean，再修 3 個小建議。

- C1 style-guide「AI panel」改成通用描述，並註明第 4 節只留在專案。
- W3 index 補 CSV 規則（挑 General／Mobile／Platform/*，deprecated 用 Replacement ID），拿掉寫死的 88。
- W4 三份 guide 補「構圖」列與別名；玻璃補 Accent 列。
- W5/W6 方向頁只放名稱＋圖＋一行；guide 只寫挑中的；並排表放對話。
- W7 校準那版擴到相同範圍。W8 新風格寫回原始 repo（guide、index 列、manifest）。W9 manifest 去掉「對話」。
- S1 只有暫存／QA 截圖進 scratchpad。S2 `brief.md` 固定在 `docs/design/`。S3 差異規則只留在 style-guide。

# Unsolved Issues

- **詞彙層第二層（表現手法）**：[motion-prompt](https://github.com/showheyohtaki/motion-prompt)（MIT，168 個手法名，附會動範例）建議收錄 `catalog.tsv`，style guide 加「手法」列、高峰時刻必須是有名字的手法。尚待使用者決定收法（收錄／只裝他們的 skill／兩者）。
- 其他候選來源未細看：superdesign-prompts（128 套風格 spec，MIT）、design-ai（真實網站 DESIGN.md，MIT）、ui-patterns.com（170 模式，僅連結）、UI UX Pro Max 的 `landing`／`app-interface`（版面模式）。字體手法、色彩手法目前沒有現成資料庫。
- StyleKit、UI Style Guide、designprompts.dev 仍未查證。
- `styles/images/` 的 6 張圖來源與授權不明（使用者上傳，疑似第三方作品），已隨 10/29 commit 同步；之後可改成只放連結＋tokens。
- 新版 SKILL 未實跑；`~/.claude/design-taste.json` 從未被寫過。
- `pdftoppm` 缺（`brew install poppler`）。
