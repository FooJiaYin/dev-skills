---
name: prd
description: |
  Compose a unified PRD.md by integrating scattered docs (meeting notes, planning docs, design guides,
  feature specs, Notion/Slack decisions) into a single source of truth. Use when user says "寫 PRD",
  "PRD.md", "整合 docs", "compose a PRD", or wants a top-level product reference for a project with
  scattered planning artifacts — even when "PRD" isn't said explicitly. NOT for greenfield
  "requirements from one-line idea" — use the `spec` skill instead.
---

# PRD Skill

PRD 是 **integrator**：把零散的決策（meeting notes、spec、Figma 註解、Slack/Notion 對話）整合成單一可信來源。不在這裡發明新需求 — 那是上游 planning meeting 或下游 feature spec 的事。

## Workflow

1. **盤點來源** — 多數專案決策住 `docs/meetings/`、Notion 會議 DB、Plaud 逐字稿；少數成熟專案才有完整 `docs/references/`。問使用者：決策實際住哪裡？v1 / v2 衝突哪個算數？
2. **Survey codebase** — 列出實際 routes / pages。§3 以實作為準，不寫計畫書理想態。**若是 greenfield（沒有 routes/pages 可掃，純 docs 階段）**：跳過此步，把 §3 標題改成「擬議頁面架構（Proposed）」並在開頭一行註明「尚未實作，以會議決策推導」，避免讀者誤把 PRD 當實作現況。
3. **3 個關鍵問題上限**：v1/v2 衝突哪個是現行？meeting decided 但沒 ship 怎麼處理？使用者最在意哪一節？
4. **一次寫完** — 內部一致性比逐步 commit 重要。

## Outline

```
1. 產品目標

2. 流程說明
   - 流程總覽（表格 + 角色 + 對應頁面 anchor）
   - 自動化流程（事件驅動 / 排程 / 條件觸發類）
   - 頁面流程（使用者操作走過的頁面序列）
   - 各重要流程一節

3. 頁面規劃
   - Layout（每頁共用的視覺結構，如 header / footer / nav / sidebar）
   - 各功能區一節，每頁包含：
      - 視覺結構：哪些 component / 區塊組成
      - 資料顯示欄位：每塊顯示什麼資料
      - 行為邏輯：
         · 使用者操作流程（從進頁到離頁）
         · 點擊後會發生什麼事（各 CTA / icon / link 的行為）
         · 錯誤處理與提示（餘額不足 / 條件不符 / 網路失敗 / 空狀態）

4. 自動化流程（總表）
   - 觸發條件（什麼事件 / 什麼時點觸發）
   - 執行動作（系統會做什麼）
   - 對應流程 / 頁面（連回 §2 / §3）

5. UI/UX 設計風格指引

6. 權限規劃（角色 + 行為權限 + 資料權限 + 升降級state machine）

7. 附件 （機制細節 + 來源文件連結）
```

Skip 任何不適用的章節 — 例如沒有自動化流程就不寫 §4；沒有明確角色權限規劃就不寫 §6。

## Writing patterns

**版本差異** — 主文寫現行版本，舊版差異用 inline italics。只標重要決策反轉，不標文字潤飾。

```
讀者線上借閱後 14 天內任一合作館取書。
*(v1→v2 變更：原本僅本館 + 7 天)*
```

**頁面段落** — bullet 結構，每頁 8-20 行。涵蓋視覺結構、資料、動態狀態、錯誤處理。不寫 1-2-3 步驟（那是 QA checklist）。

```markdown
#### 書籍詳情

**角色**：讀者主視角

- **Hero**：書封 + 書名 + 作者 + ISBN
- **Info**：分類 / 頁數 / 館藏館別 / 書架位置
- **狀態徽章**：可借 / 已借出（顯示預計歸還）/ 預約中（順位 N）/ 不外借
- **Sticky CTA**（依狀態）：
  - 可借：「立即借閱」
  - 已借出：「預約取書（順位 N）」
  - 額度已滿：disabled「您已借滿 10 本」+ 引導我的借閱
  - 有逾期：disabled「請先繳清逾期費用」
```

**使用者語言** — 不寫任何開發者術語（如「API call」），或技術實現細節（如「RLS」）。只寫使用者能理解的行為和狀態。不寫任何假設（如「系統會自動更新」），有假設就寫 `[Questions]`。

| ❌ Don't | ✅ Do |
|---|---|
| `useUserStore.currentRole` | 目前身份 |
| `localStorage loan-session-v1` | 借閱 session |
| `BarcodeDetector + getUserMedia` | 條碼掃描（含手動 fallback）|
| `WebSocket / FCM / APNS` | 即時更新 / 手機推播 |

**附件策略** — 壓縮 + 連結，不 copy-paste。一行 scope + 一張 canonical 表 + 3-5 個關鍵決策 + 連回原 doc。

## Output

預設寫到 `docs/PRD.md`。完成後簡短回報：總長度、整合了哪些 sources、做了什麼取捨、有沒有 v1/v2 衝突待裁示。不問 sign-off 問題，直接交付。

## See also

- `spec` — 從 PRD.md 產出細部規範（API / schema）
- `update-docs` — 既有文件增量更新
- `report` — 一次性 session 報告
