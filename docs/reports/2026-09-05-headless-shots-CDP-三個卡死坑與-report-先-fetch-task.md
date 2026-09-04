# headless-shots 的三個 CDP 卡死坑 ＋ /report 從任務計畫接手時先 fetch

## 摘要

```
來源：sparktoy-erp 實作 C1–C7 時踩到的 friction（/improve 盤出）

headless-shots  診斷成本最高的三件事，文件完全沒提
  window.confirm      → 凍結整條 CDP，伺服器收不到請求，後續 evaluate 全部不回
  導航 click          → Runtime.evaluate 永不回應，必須射後不理
  captureScreenshot   → 卡死後拖垮整條連線，Promise.race 也救不回來

/report         接手別的 session 的 _plan-*.md 時，靜默落到 fresh 分支
  沒有 docs/tasks/<slug>.md → 逐任務出報告的路整條消失
  症狀：一份報告蓋七筆任務，事後接不回任何一筆
```

# Description

`/improve` 從一段 sparktoy-erp 的實作 session 盤出四項 friction，其中兩項屬技能層級（另兩項進了全域 `CLAUDE.md`，不在本 repo）。共同點是**都要踩到才會發現**，而且症狀都偽裝成別的問題。

# Changes Made

- **`skills/headless-shots/SKILL.md`** — Gotchas 補五條：
  - `window.confirm` / `alert` 會凍結整條 CDP，且**伺服器完全收不到請求**，表現得像「按鈕沒反應」；必須 `Page.enable` + 自動 accept `javascriptDialogOpening`。表單的未儲存／繼承／刪除確認框最常觸發。
  - 會觸發導航的 click 必須 fire-and-forget（裸 `ws.send`，不 await），結果改由 DB 驗證。
  - `Page.captureScreenshot` 卡死後會讓**後續所有** CDP 呼叫一起吊住，對它加 `Promise.race` 超時無效；寫入路徑的驗證優先用 DOM 斷言 + SQL，截圖留到最後或直接不用。
  - 腳本要有硬超時，讓卡死大聲失敗而不是吊住工具呼叫。
  - dev 模式 server action 首次呼叫要編譯，送出後至少等 20s 再殺 Chrome，否則動作被中斷、什麼都沒寫入。

- **`skills/headless-shots/scripts/drive-example.mjs`** — 範本補上對話框處理與硬超時，兩個送出點都改成 fire-and-forget（原本 A 情境 `await` + 4s、B 情境同樣寫法）。

- **`skills/report/SKILL.md`** — §0 目標解析前新增 step 0：若本次是照 `docs/tasks/_plan-*.md` 實作、卻沒有任何 `docs/tasks/<slug>.md` 相符，**先 `/fetch-task` 該計畫建立／連結的任務再解析目標**。

# Result

三個檔案共 23+/6−。修改後對檔案 `grep` 驗證（不是看腳本輸出）。

`/report` 那條的根因值得記著：**`/create-tasks` 的 checkout picker 只在建立任務的那個 session 跑**。接手的 session 拿到計畫檔但沒有任務檔，於是 §0 的「0 matches → fresh report」靜默生效，`Target = task file` 與多任務切分兩條路同時消失。實際症狀是一份報告蓋七筆 Notion 任務、事後接不回去，連帶那次的 commit 也因為 migration 綁定與共用檔案而拆不動。

# Unsolved Issues

- `attach-plan.sh` 的 `prepend` 對無 frontmatter 的報告是「insert after line 1」，會把緊接標題的 `## 摘要` 推到計畫之後（本次實測被推到第 237 行）。已提出但使用者選擇 Skip，維持手動搬回。
