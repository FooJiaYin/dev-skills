// Fictional project demonstration. No live tools or external writes.
window.DEV_SKILLS_DEMOS = window.DEV_SKILLS_DEMOS || {};
window.DEV_SKILLS_DEMOS["discuss"] = {
  "id": "discuss",
  "chapter": "prepare",
  "title": "動手之前，先把方向聊清楚",
  "intro": "同一個需求常常有好幾種做法，太快動手，後面就容易重來。它會先看專案現況，把選項、代價和還沒想清楚的地方攤開，陪你選好方向，再進入規劃與實作。",
  "input": "需求、限制與專案現況",
  "output": "docs/plans/2026-09-21-庫存預留與取消.md",
  "artifact": "# 庫存預留與取消實作計畫\n\n日期：2026-09-21。狀態：方案已選定（B），尚未實作。來源任務：`docs/tasks/庫存預留與取消-3f9a21.md`；會議依據：`docs/meetings/2026-09-18-庫存預留與取消討論.md` 四、五、六章。\n\n本計畫依本次討論整理。會議決議優先於現有程式行為；本次僅新增計畫，不修改程式、不執行 migration。\n\n## 摘要（現在❌ → 改後✓）\n\n```\n預留     ❌ 業務在群組問倉管還剩幾件，口頭保留；Excel 一天更新一次\n         ✓ 預留頁送出 → 伺服器確認可用數量並扣除，一次完成\n超賣     ❌ 兩人同時看到「剩 1 件」都能預留\n         ✓ 送出時鎖定庫存列，只有一人成功，另一人看到「庫存不足」\n重複送出 ❌ 連按兩次 = 兩筆預留\n         ✓ 同一個 request_id 只算一次，第二次回傳既有預留\n取消     ❌ 無\n         ✓ 業務取消自己的預留，數量還回可用庫存；已出貨明確拒絕\n我的預留 ❌ 無\n         ✓ 預留清單列出自己的預留與狀態，可從清單取消\n```\n\n## 1. 目標與範圍\n\n讓業務在獨立的預留頁看到扣除預留後的可用數量，送出預留時由伺服器確認庫存，不再超賣；客人不要時，業務可以自己取消並把數量還回庫存。\n\n- 本輪：預留、取消、庫存不足停止預留、重複送出只算一次、我的預留清單。\n- 不在範圍：缺貨通知、預留自動到期、倉管代為取消（待會議確認）、退貨流程（維持人工）。\n- 不動商品列表：另一位同事正在調整，預留頁做成獨立頁面 `/reservations`。\n\n## 2. 已確認的產品設計\n\n| 項目 | 決策 |\n| --- | --- |\n| 可用數量 | 實際庫存 − 狀態為 reserved 的預留總數 |\n| 庫存不足 | 停用送出按鈕，顯示「庫存不足」與剩餘數量 |\n| 重複送出 | 前端每次開啟表單產生 `request_id`，伺服器以 unique 去重 |\n| 同時預留 | 伺服器在同一個交易裡鎖定庫存列再檢查、扣除 |\n| 取消權限 | 只有建立者本人；倉管代取消待確認 |\n| 已出貨 | 取消回傳 `SHIPPED`，畫面維持已預留 |\n| 取消紀錄 | 以預留狀態與建立者回答「誰取消了哪一筆」，不另做紀錄頁 |\n\n## 3. 方案比較：最後一件庫存\n\n| | A｜只在畫面上判斷 | B｜送出時由伺服器確認並預留 |\n| --- | --- | --- |\n| 作法 | 前端讀可用數量，不足就停用按鈕 | server action 在同一個交易裡檢查並扣除 |\n| 同時預留 | 兩人都成功 → 超賣 | 只有一人成功，另一人收到 `INSUFFICIENT_STOCK` |\n| 重複送出 | 需另外處理 | `request_id` unique 一併處理 |\n| 成本 | 最少 | 多一道交易與錯誤處理 |\n\n**選定：B**。會議要求「不能超賣」，A 守不住；B 多出的交易處理集中在一支 server action。\n\n## 4. 資料與權限設計\n\n### 4.1 資料表\n\n```sql\ncreate table stock_reservations (\n  id           uuid primary key default gen_random_uuid(),\n  product_id   uuid not null references products(id),\n  quantity     int  not null check (quantity > 0),\n  reserved_by  uuid not null references users(id),\n  status       text not null default 'reserved'\n               check (status in ('reserved', 'cancelled', 'shipped')),\n  request_id   text not null unique,\n  created_at   timestamptz not null default now(),\n  cancelled_at timestamptz\n);\n```\n\n- `available_stock` view：每個商品的實際庫存減去 reserved 預留總數。\n- 出貨流程既有的出貨單建立時，把對應預留改成 `shipped`（本輪只加欄位判斷，不改出貨流程）。\n\n### 4.2 權限\n\n- 預留：具備業務角色的使用者。\n- 取消：`reserved_by = 目前使用者` 且 `status = reserved`。\n- 業務與倉管角色由「員工登入」任務補上；本輪先以既有 `role = sales` 判斷。\n\n## 5. 狀態與核心操作\n\n```\nreserveStock(productId, quantity, requestId)\n  └─ 交易開始\n     ├─ request_id 已存在？ → 回傳既有預留（不重複扣除）\n     ├─ 鎖定 stock 列，讀 available\n     ├─ available < quantity？ → INSUFFICIENT_STOCK\n     └─ 寫入 reserved 預留 → 提交\n\ncancelReservation(id)\n  ├─ 不是本人？ → FORBIDDEN\n  ├─ status = shipped？ → SHIPPED\n  └─ 改為 cancelled、寫入 cancelled_at → 數量回到 available\n```\n\n## 6. 實作階段與檔案範圍\n\n### 階段一：資料結構\n\n- `migrations/0012_stock_reservations.sql` — 資料表、unique 索引、`available_stock` view\n\n### 階段二：伺服器操作\n\n- `src/lib/reservations/actions.ts` — `reserveStock`、`cancelReservation`\n- `src/lib/reservations/data.ts` — `getAvailableQty`、`listReservations`\n\n### 階段三：畫面\n\n- `src/app/(main)/reservations/page.tsx` — 預留頁與我的預留清單\n- `src/app/(main)/reservations/reserve-button.tsx` — 預留與取消按鈕、錯誤訊息\n\n### 階段四：驗收與文件\n\n- `README.md` 功能列表、`docs/PRD.md` 取消規則\n\n## 7. Verification / 驗收\n\n- 同一 `request_id` 送出兩次 → 只有一筆預留，可用數量只扣一次\n- 兩個帳號同時預留最後一件 → 一人成功、一人收到「庫存不足」，可用數量停在 0\n- 庫存不足時 → 送出按鈕停用，顯示剩餘數量\n- 取消別人的預留 → 被拒，畫面維持原狀\n- 取消已出貨的預留 → 被拒，畫面保留原本的預留狀態\n- 取消自己的預留 → 可用數量加回\n- `yarn typecheck`、`yarn lint`、`yarn test reservations`\n\n## 8. 待確認\n\n- 倉管是否可代為取消（@佩雯 會後確認）；若可以，取消權限改為「本人或倉管」並在清單標示代取消。\n- 預留自動到期與缺貨通知：下次會議討論，本輪不預留欄位以外的設計。\n\n## 9. 依據\n\n- 會議記錄 四、庫存預留規則；五、取消預留；六、畫面與操作\n- 任務 `庫存預留與取消`（Notion）",
  "why": "把選項與代價講清楚，由你選方向；不把尚未決定的猜測直接寫成程式。",
  "routes": [
    "notion",
    "github"
  ],
  "steps": [
    "讀現況",
    "比較方案",
    "確認範圍"
  ],
  "messages": [
    [
      "user",
      "/discuss 先討論庫存預留，不寫程式。"
    ],
    [
      "skill",
      "/discuss"
    ],
    [
      "tool",
      "Read · 預留任務、商品資料與現有登入流程"
    ],
    [
      "assistant",
      "目前商品有可用庫存，但還沒有預留庫存的處理。我看到兩種作法：只在畫面判斷比較快，不過兩個人同時預留可能超賣；送出時再確認並預留庫存，會多一點工作，但比較穩。"
    ],
    [
      "user",
      "選第二個。缺貨通知先不做。"
    ],
    [
      "assistant",
      "好。取消之後可用數量就釋出；如果另一個人剛好搶先預留，畫面會說庫存不足，不會顯示成功。"
    ],
    [
      "user",
      "可以，就這樣規劃。"
    ],
    [
      "artifact",
      "Write · docs/plans/2026-09-21-庫存預留與取消.md\n選定方案、暫不做的項目、檔案範圍與驗收項目。"
    ],
    [
      "assistant",
      "計畫存到 docs/plans/2026-09-21-庫存預留與取消.md 了。選定方案、暫不做的項目、實作步驟和驗收項目都在裡面；這輪還沒有改程式。",
      {
        "documents": [
          "discuss"
        ]
      }
    ]
  ]
};
