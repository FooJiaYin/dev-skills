---
session: 2026-09-25-interactive-dev-skills-site (01a0d3e4-ea97-7152-b043-b64458a59149), 2026-09-25-site-mobile-chat-and-diagram-lines (b3ae627e-d6b0-42c7-946d-9aebef3bd8f6)
---

# Interactive dev-skills site

# Description

把原本的文章構想改為 `docs/site/` 的互動式 IDE 風格網站。本文記錄這輪網站設計與實作；右側的琢奧 ERP 對話與文件是去識別化、虛構的流程示範，不是一次真實 session 的逐字重播。

# Changes Made

- 用親切、通用的敘事先解釋為什麼需要這套工作方法，再透過不同的圖像語言說明資料整理、開工、Quick／Full、品質確認、交接、記憶與改進。主頁說明不帶入示範專案細節；Notion 與 GitHub 在 lifecycle 中各有路徑。`docs/site/app.js`, `docs/site/methods.js`, `docs/site/styles.css`
- 中間內容維持連續捲動；左側 skill 與相關文件、右側 Claude Code／Codex 模擬對話能互相對應。每一步的 CTA 可重播對應階段；文件從預覽卡在 IDE 內的新 tab 開啟。`docs/site/app.js`, `docs/site/index.html`, `docs/site/document.js`
- 對話中的使用者指令先在輸入框打出再送出；選完問題選項後不重打一則使用者訊息。執行中的文件連結留在 agent 回覆裡。`docs/site/app.js`, `docs/site/styles.css`
- Memory 用團隊資料、單份 `report.md`、原始 session log 三層呈現；Improve 用「這輪卡點 → 具體改法 → 決定收進哪裡 → 下輪用得上」及分流線呈現，提案只在對話中，不假裝另有文件。`docs/site/methods.js`, `docs/site/demos/improve.js`, `docs/site/document.js`, `docs/site/styles.css`
- 結尾改為「讓你的 agent 認識 dev-skills。」並列 Claude Code、Codex 安裝步驟，保留完整安裝說明；示範按鈕在右側對話（手機為浮動對話框）播放，不會執行安裝。`docs/site/app.js`, `docs/site/styles.css`
- 手機版對話改為右下角浮動按鈕，點開才顯示對話框，取代原本各段落內嵌的對話；桌面版不變。按鈕只放對話圖示與正在示範的 skill 名稱。對話框開啟時，按鈕移到對話框右上方變成圓形圖示（Messenger 式聊天頭像），再點一次即收合；對話框從右下角展開、關閉時收回，並尊重「減少動態效果」設定。各步驟的「試試 /skill」直接打開對應對話；Esc、點背景都能關閉，開啟時 Tab 焦點留在對話框內。`docs/site/app.js`, `docs/site/styles.css` _(2026-09-25: 由各段內嵌對話改為浮動對話框)_
- 手機版圖解連線：Improve 在窄螢幕改為直向順序，步驟線與分流線接到「收進哪裡」的選項再接最後一步。lifecycle 的 GitHub 分支線原本以 CSS 寫死座標（`preserveAspectRatio="none"`），換寬度就沒接到卡片、回程線斷開並多出鉤子、線穿過文字；改為 ≤580px 時由 JS 量卡片實際位置畫直角線，⑂ 圖示放在往下的線上作分支點，說明文字收在回程線左側，桌面沿用原路徑。「把討論接成工作」的直向箭頭原用旋轉的 `›` 字元，偏離線條且線超出箭頭尖；改為以 CSS 邊框畫、置中於線、尖端對齊線尾。`docs/site/app.js`, `docs/site/styles.css` _(2026-09-25)_

# Verification

- `node docs/site/check-demos.mjs`：16 個精選示範與文件視圖、四個排除 skill、CTA 和情境內容檢查通過。
- `node docs/site/check-browser.mjs`：本機 Chrome 檢查桌面與手機寬度、連續流程、對話與 host 切換、IDE tab、文件連結、重播及安裝示範，通過且無 JS 錯誤。測試一度期待 Claude Code 文案卻沿用前一步的 Codex host；先明確切回 Claude Code 後再驗證切換，通過。
- GitHub Pages Action `36072983036` 對 `07b01c7` 部署成功；公開站 `https://foojiayin.github.io/dev-skills/app.js` 讀回包含 `installConversations` 與結尾安裝示範。這是部署檔案讀回，未對公開站再次跑完整瀏覽器互動檢查。
- _(2026-09-25 手機對話框與圖解連線)_ `check-browser.mjs` 新增手機斷言：一開始只有右下角按鈕、點開後對話框為 `role=dialog` 且有展開動畫、關閉先播收合動畫再回到按鈕、文件 chip 從對話框開啟、安裝示範在對話框內切換 host。兩個工作階段的修改合併後重跑 `node docs/site/check-demos.mjs` 與 `node docs/site/check-browser.mjs`，全部 PASS、無 JS 錯誤；Codex 端另跑過 320px 寬度與減少動態效果。
- _(2026-09-25)_ 以 headless Chrome（CDP，`mobile: true`、2x）截圖檢查 lifecycle 圖解在 360／390／430px、「把討論接成工作」箭頭在 390px、開啟中的對話框在 390px：連線落在卡片中心、箭頭置中且尖端對齊線尾、聊天頭像位於對話框右上方。桌面與 581–900px 寬度未截圖，只靠 check-browser 的桌面檢查。

# Suggested Doc Updates

- `docs/site/demos/README.md` 可補充「Improve 提案只在對話」、「安裝示範不執行指令」與目前的四段導覽；此檔在共享工作樹中屬其他視窗的未追蹤工作，Quick 模式只提議、不修改。
- 安裝來源的正式說明若有變更，應同步核對網站結尾的 Claude Code 與 Codex 指令；本輪沒有改 README。
- `docs/site/demos/README.md:19` 仍寫「the inline conversation on mobile」；手機版已改為從浮動按鈕開啟的對話框，應改寫此句。_(2026-09-25)_

# Updates

- 使用者要求手機版對話改為浮動按鈕加對話框，接著要求修手機圖解的線、加 Messenger 式開啟動畫（Codex 工作階段 01a0d3e4）。
- 另一個 Claude 工作階段（b3ae627e）接著修 lifecycle 分支線；途中使用者追加：刪掉按鈕上的「看對話」文字、對話框開啟時圖示要在對話框右上方（像 Messenger）、修正「把討論接成工作」的歪箭頭。
- impeccable 設計檢查指出聊天頭像移動時用 `bottom`／`padding` 做 transition 會造成 layout thrash，改成只對 `transform: translateY(...)` 做 transition，截圖確認位置不變。
- 對話框標題列的 ✕ 關閉鈕保留，所以開啟時有兩種關閉方式；若要完全照 Messenger 只留頭像，可再移除 ✕。

# Result

網站在本機完成互動與響應式檢查，已透過 GitHub Pages 發布並讀回新版本的腳本。提交排除了其他視窗的修改，尤其 `docs/site/index.html` 的外來 favicon 連結；那些檔案仍留在工作樹，沒有被刪除。

_(2026-09-25)_ 手機版的對話改為浮動按鈕加對話框，圖解連線與箭頭在窄螢幕上都接回卡片。兩個工作階段對 `app.js`／`styles.css` 的修改互相疊加、無法拆開，依使用者決定合併成一個 commit；`check-browser.mjs` 一併提交。
