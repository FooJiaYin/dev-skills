---
session: 2026-09-25-interactive-dev-skills-site (01a0d3e4-ea97-7152-b043-b64458a59149)
---

# Interactive dev-skills site

# Description

把原本的文章構想改為 `docs/site/` 的互動式 IDE 風格網站。本文記錄這輪網站設計與實作；右側的琢奧 ERP 對話與文件是去識別化、虛構的流程示範，不是一次真實 session 的逐字重播。

# Changes Made

- 用親切、通用的敘事先解釋為什麼需要這套工作方法，再透過不同的圖像語言說明資料整理、開工、Quick／Full、品質確認、交接、記憶與改進。主頁說明不帶入示範專案細節；Notion 與 GitHub 在 lifecycle 中各有路徑。`docs/site/app.js`, `docs/site/methods.js`, `docs/site/styles.css`
- 中間內容維持連續捲動；左側 skill 與相關文件、右側 Claude Code／Codex 模擬對話能互相對應。每一步的 CTA 可重播對應階段；文件從預覽卡在 IDE 內的新 tab 開啟。`docs/site/app.js`, `docs/site/index.html`, `docs/site/document.js`
- 對話中的使用者指令先在輸入框打出再送出；選完問題選項後不重打一則使用者訊息。執行中的文件連結留在 agent 回覆裡。`docs/site/app.js`, `docs/site/styles.css`
- Memory 用團隊資料、單份 `report.md`、原始 session log 三層呈現；Improve 用「這輪卡點 → 具體改法 → 決定收進哪裡 → 下輪用得上」及分流線呈現，提案只在對話中，不假裝另有文件。`docs/site/methods.js`, `docs/site/demos/improve.js`, `docs/site/document.js`, `docs/site/styles.css`
- 結尾改為「讓你的 agent 認識 dev-skills。」並列 Claude Code、Codex 安裝步驟，保留完整安裝說明；示範按鈕在右側／手機內嵌對話播放，不會執行安裝。`docs/site/app.js`, `docs/site/styles.css`

# Verification

- `node docs/site/check-demos.mjs`：16 個精選示範與文件視圖、四個排除 skill、CTA 和情境內容檢查通過。
- `node docs/site/check-browser.mjs`：本機 Chrome 檢查桌面與手機寬度、連續流程、對話與 host 切換、IDE tab、文件連結、重播及安裝示範，通過且無 JS 錯誤。測試一度期待 Claude Code 文案卻沿用前一步的 Codex host；先明確切回 Claude Code 後再驗證切換，通過。
- GitHub Pages Action `36072983036` 對 `07b01c7` 部署成功；公開站 `https://foojiayin.github.io/dev-skills/app.js` 讀回包含 `installConversations` 與結尾安裝示範。這是部署檔案讀回，未對公開站再次跑完整瀏覽器互動檢查。

# Suggested Doc Updates

- `docs/site/demos/README.md` 可補充「Improve 提案只在對話」、「安裝示範不執行指令」與目前的四段導覽；此檔在共享工作樹中屬其他視窗的未追蹤工作，Quick 模式只提議、不修改。
- 安裝來源的正式說明若有變更，應同步核對網站結尾的 Claude Code 與 Codex 指令；本輪沒有改 README。

# Result

網站在本機完成互動與響應式檢查，已透過 GitHub Pages 發布並讀回新版本的腳本。提交排除了其他視窗的修改，尤其 `docs/site/index.html` 的外來 favicon 連結；那些檔案仍留在工作樹，沒有被刪除。
