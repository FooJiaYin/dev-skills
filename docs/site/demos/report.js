// Fictional project demonstration. No live tools or external writes.
window.DEV_SKILLS_DEMOS = window.DEV_SKILLS_DEMOS || {};
window.DEV_SKILLS_DEMOS["report"] = {
  "id": "report",
  "chapter": "handoff",
  "title": "把這輪的結果，寫給下一個接手的人",
  "intro": "一句「做完了」，還不足以讓別人接手。它會把本輪修改、重要決定、驗證結果和未完成事項整理成報告；同一輪後來有補充，就接著更新這份，不讓結果散在好幾個地方。",
  "input": "本輪對話、修改、測試與 review",
  "output": "docs/reports/2026-09-22-庫存預留與取消-3f9a21.md",
  "artifact": "---\nnotion:\n  page: https://www.notion.so/zhuoao-demo/庫存預留與取消\n  last_synced: 2026-09-22T17:04:30+08:00\nsession: 2026-09-22-庫存預留與取消 (demo-0922)\n---\n\n<!-- synced from Notion by /fetch-task · do not edit # Context locally; edits will be lost on refresh -->\n# Context\n## <mention-page url=\"https://www.notion.so/zhuoao-demo/庫存預留與取消討論\"/>\n### 會議記錄 四、庫存預留規則；五、取消預留\n## **四、庫存預留規則**\n### 1. 可用數量與上限\n- **決策**：預留數量不可超過可用庫存；庫存不足時直接停止預留，畫面顯示剩餘數量，不讓業務送出。\n- 預留成功後，可用庫存立即扣掉預留數量，其他業務看到的是扣完後的數字。\n- 可用數量的定義：實際庫存減去所有尚未取消、尚未出貨的預留。\n### 2. 重複送出與同時預留\n- 佩雯擔心網路慢時業務連按兩次，同一筆被記成兩筆預留，事後很難分辨哪一筆是多的。**決策**：同一筆送出只算一次。\n- 志豪提到兩位業務同時搶最後一件時，如果只在畫面上判斷，兩人都會看到「剩 1 件」並送出成功，一樣會超賣。需要在送出的那一刻由系統一起確認庫存，只讓其中一人成功。\n- 具體作法由工程會後提方案，確認後再實作；會中只確定「不能超賣」這個結果。\n### 3. 預留的保留期限\n- 怡君希望預留能保留約三天，讓客人有時間確認；佩雯擔心預留一直不取消會把庫存卡住。\n- 志豪表示自動到期釋放需要排程與通知，工作量不小。**本次未定**，先不做自動到期，列入待定事項。\n---\n## **五、取消預留**\n### 1. 誰可以取消\n- **決策**：業務可以取消自己建立的預留，取消後數量還回可用庫存。\n- 倉管能否代業務取消（例如業務請假、客人直接打給倉庫），佩雯要先問倉庫同事的作業習慣，**本次未定**。\n### 2. 出貨後的限制\n- **決策**：已出貨的預留不可由業務自行取消，需走退貨流程；系統要明確拒絕，不能讓畫面看起來像取消成功。\n- 佩雯補充，退貨流程目前由倉庫人工處理，這次不需要做進系統。\n### 3. 取消紀錄\n- 怡君希望事後能查到是誰、在什麼時候取消了哪一筆預留，避免業務之間的誤會。\n- 志豪表示預留保留狀態（已預留／已取消／已出貨）即可回答這個問題，不需另外做紀錄頁。\n\n# Plan\n\n# 庫存預留與取消實作計畫\n\n日期：2026-09-21。狀態：方案已選定（B），尚未實作。來源任務：`docs/tasks/庫存預留與取消-3f9a21.md`；會議依據：`docs/meetings/2026-09-18-庫存預留與取消討論.md` 四、五、六章。\n\n本計畫依本次討論整理。會議決議優先於現有程式行為；本次僅新增計畫，不修改程式、不執行 migration。\n\n## 摘要（現在❌ → 改後✓）\n\n```\n預留     ❌ 業務在群組問倉管還剩幾件，口頭保留；Excel 一天更新一次\n         ✓ 預留頁送出 → 伺服器確認可用數量並扣除，一次完成\n超賣     ❌ 兩人同時看到「剩 1 件」都能預留\n         ✓ 送出時鎖定庫存列，只有一人成功，另一人看到「庫存不足」\n重複送出 ❌ 連按兩次 = 兩筆預留\n         ✓ 同一個 request_id 只算一次，第二次回傳既有預留\n取消     ❌ 無\n         ✓ 業務取消自己的預留，數量還回可用庫存；已出貨明確拒絕\n我的預留 ❌ 無\n         ✓ 預留清單列出自己的預留與狀態，可從清單取消\n```\n\n## 1. 目標與範圍\n\n讓業務在獨立的預留頁看到扣除預留後的可用數量，送出預留時由伺服器確認庫存，不再超賣；客人不要時，業務可以自己取消並把數量還回庫存。\n\n- 本輪：預留、取消、庫存不足停止預留、重複送出只算一次、我的預留清單。\n- 不在範圍：缺貨通知、預留自動到期、倉管代為取消（待會議確認）、退貨流程（維持人工）。\n- 不動商品列表：另一位同事正在調整，預留頁做成獨立頁面 `/reservations`。\n\n## 2. 已確認的產品設計\n\n| 項目 | 決策 |\n| --- | --- |\n| 可用數量 | 實際庫存 − 狀態為 reserved 的預留總數 |\n| 庫存不足 | 停用送出按鈕，顯示「庫存不足」與剩餘數量 |\n| 重複送出 | 前端每次開啟表單產生 `request_id`，伺服器以 unique 去重 |\n| 同時預留 | 伺服器在同一個交易裡鎖定庫存列再檢查、扣除 |\n| 取消權限 | 只有建立者本人；倉管代取消待確認 |\n| 已出貨 | 取消回傳 `SHIPPED`，畫面維持已預留 |\n| 取消紀錄 | 以預留狀態與建立者回答「誰取消了哪一筆」，不另做紀錄頁 |\n\n## 3. 方案比較：最後一件庫存\n\n| | A｜只在畫面上判斷 | B｜送出時由伺服器確認並預留 |\n| --- | --- | --- |\n| 作法 | 前端讀可用數量，不足就停用按鈕 | server action 在同一個交易裡檢查並扣除 |\n| 同時預留 | 兩人都成功 → 超賣 | 只有一人成功，另一人收到 `INSUFFICIENT_STOCK` |\n| 重複送出 | 需另外處理 | `request_id` unique 一併處理 |\n| 成本 | 最少 | 多一道交易與錯誤處理 |\n\n**選定：B**。會議要求「不能超賣」，A 守不住；B 多出的交易處理集中在一支 server action。\n\n## 4. 資料與權限設計\n\n### 4.1 資料表\n\n```sql\ncreate table stock_reservations (\n  id           uuid primary key default gen_random_uuid(),\n  product_id   uuid not null references products(id),\n  quantity     int  not null check (quantity > 0),\n  reserved_by  uuid not null references users(id),\n  status       text not null default 'reserved'\n               check (status in ('reserved', 'cancelled', 'shipped')),\n  request_id   text not null unique,\n  created_at   timestamptz not null default now(),\n  cancelled_at timestamptz\n);\n```\n\n- `available_stock` view：每個商品的實際庫存減去 reserved 預留總數。\n- 出貨流程既有的出貨單建立時，把對應預留改成 `shipped`（本輪只加欄位判斷，不改出貨流程）。\n\n### 4.2 權限\n\n- 預留：具備業務角色的使用者。\n- 取消：`reserved_by = 目前使用者` 且 `status = reserved`。\n- 業務與倉管角色由「員工登入」任務補上；本輪先以既有 `role = sales` 判斷。\n\n## 5. 狀態與核心操作\n\n```\nreserveStock(productId, quantity, requestId)\n  └─ 交易開始\n     ├─ request_id 已存在？ → 回傳既有預留（不重複扣除）\n     ├─ 鎖定 stock 列，讀 available\n     ├─ available < quantity？ → INSUFFICIENT_STOCK\n     └─ 寫入 reserved 預留 → 提交\n\ncancelReservation(id)\n  ├─ 不是本人？ → FORBIDDEN\n  ├─ status = shipped？ → SHIPPED\n  └─ 改為 cancelled、寫入 cancelled_at → 數量回到 available\n```\n\n## 6. 實作階段與檔案範圍\n\n### 階段一：資料結構\n\n- `migrations/0012_stock_reservations.sql` — 資料表、unique 索引、`available_stock` view\n\n### 階段二：伺服器操作\n\n- `src/lib/reservations/actions.ts` — `reserveStock`、`cancelReservation`\n- `src/lib/reservations/data.ts` — `getAvailableQty`、`listReservations`\n\n### 階段三：畫面\n\n- `src/app/(main)/reservations/page.tsx` — 預留頁與我的預留清單\n- `src/app/(main)/reservations/reserve-button.tsx` — 預留與取消按鈕、錯誤訊息\n\n### 階段四：驗收與文件\n\n- `README.md` 功能列表、`docs/PRD.md` 取消規則\n\n## 7. Verification / 驗收\n\n- 同一 `request_id` 送出兩次 → 只有一筆預留，可用數量只扣一次\n- 兩個帳號同時預留最後一件 → 一人成功、一人收到「庫存不足」，可用數量停在 0\n- 庫存不足時 → 送出按鈕停用，顯示剩餘數量\n- 取消別人的預留 → 被拒，畫面維持原狀\n- 取消已出貨的預留 → 被拒，畫面保留原本的預留狀態\n- 取消自己的預留 → 可用數量加回\n- `yarn typecheck`、`yarn lint`、`yarn test reservations`\n\n## 8. 待確認\n\n- 倉管是否可代為取消（@佩雯 會後確認）；若可以，取消權限改為「本人或倉管」並在清單標示代取消。\n- 預留自動到期與缺貨通知：下次會議討論，本輪不預留欄位以外的設計。\n\n## 9. 依據\n\n- 會議記錄 四、庫存預留規則；五、取消預留；六、畫面與操作\n- 任務 `庫存預留與取消`（Notion）\n\n# Changes Made\n\n```\n會議決議                    現況 ❌                          改後 ✓\n四、1 庫存不足停止預留      只有庫存數量，無預留概念         available_stock = 庫存 − reserved 預留\n四、2 同一筆只算一次        連按兩次 = 兩筆                  request_id unique，第二次回傳既有預留\n四、2 同時搶最後一件        只靠畫面判斷會超賣               交易內鎖定庫存列，只有一人成功\n五、1 業務取消自己的預留    無                               cancelReservation 限本人、數量加回\n五、2 已出貨不可取消        無                               回傳 SHIPPED，畫面維持已預留\n六 我的預留清單             無                               /reservations 清單可直接取消\n```\n\n- `migrations/0012_stock_reservations.sql`：新增 `stock_reservations`（`status` reserved／cancelled／shipped、`request_id` unique、`cancelled_at`）與 `available_stock` view；檔頭補上用途註解（NT-02）。\n- `src/lib/reservations/actions.ts`：`reserveStock` 在同一個交易裡鎖住庫存列，檢查可用數量後寫入預留；重複的 `request_id` 直接回傳既有預留，不再扣除。`cancelReservation` 只允許本人取消 reserved 狀態；他人回 `FORBIDDEN`，已出貨回 `SHIPPED`。\n- `src/lib/reservations/data.ts`：`getAvailableQty` 讀 `available_stock`；`listReservations` 依建立時間列出目前使用者的預留。\n- `src/lib/reservations/messages.ts`：錯誤碼對應訊息（`INSUFFICIENT_STOCK`、`FORBIDDEN`、`SHIPPED`），頁面與按鈕共用（NT-01）。\n- `src/app/(main)/reservations/page.tsx`：預留頁顯示剩餘數量與我的預留清單；獨立頁面，不動商品列表。\n- `src/app/(main)/reservations/reserve-button.tsx`：庫存不足時停用按鈕並顯示剩餘數量；每次開啟表單產生 `request_id`；取消失敗時還原先前狀態並顯示原因（WR-01）。\n\n```sql\nselect s.qty - coalesce(sum(r.quantity), 0) as available\nfrom stock s\nleft join stock_reservations r\n  on r.product_id = s.product_id and r.status = 'reserved'\nwhere s.product_id = $1\ngroup by s.qty\nfor update of s;\n```\n\nResult: `yarn migrate`、`yarn typecheck`、`yarn lint`、`yarn test reservations` 全過。\n\n# Verification\n\n- `yarn test reservations`（9 項全過）— 同一 `request_id` 送出兩次，只產生 1 筆預留；可用數量 12 → 11，不是 10。\n- 併發測試：兩個帳號以 `Promise.all` 同時預留最後一件 — 1 筆成功、1 筆回 `INSUFFICIENT_STOCK`，可用數量停在 0。\n- 手動：可用數量 0 時打開預留頁 — 送出按鈕停用，顯示「庫存不足，剩餘 0 件」。\n- 手動：業務 A 取消業務 B 的預留 — 回 `FORBIDDEN`，畫面維持原狀。\n- 手動：取消已出貨的預留 — 伺服器回 `SHIPPED`，畫面仍顯示已預留並提示「已出貨，請走退貨流程」；之後取消其他預留正常。\n- 手動：取消自己的預留 — 狀態變 cancelled，可用數量加回 1。\n- 未測：正式環境資料量下的預留清單載入速度；倉管角色（尚未建立）。\n\n# Result\n\n- 業務可以在預留頁預留與取消；庫存不足時停止預留，兩人搶最後一件只有一人成功，重複送出不重複扣除。\n- 已出貨的預留會被明確拒絕，畫面不會誤顯示取消成功。\n- 尚未 push、尚未部署；分支 `feat/stock-reservation`。\n- 影響：可用數量改由 `available_stock` 計算；商品列表的「剩餘數量」之後應改讀這個 view，已告知負責商品列表的同事。\n\n# Updates\n\n- **Step-by-Step**：先完成 migration 與 server action，再做畫面。第一次跑測試時，取消已出貨的預留回傳 OK 而不是 `SHIPPED`，原因是狀態判斷寫在更新之後；改成先檢查狀態再更新後通過。\n- /code-review 六個角度找到 4 項：1 Warning、1 Suggestion、2 Nit。\n- Fixed [Warning] `src/app/(main)/reservations/reserve-button.tsx:48` — 取消被拒時畫面清掉原本的預留；改為失敗時還原先前狀態並顯示原因，/code-review 複查通過。\n- Fixed [Nit] `src/app/(main)/reservations/page.tsx:19` — 「庫存不足」訊息重複定義；集中到 `messages.ts`。\n- Fixed [Nit] `migrations/0012_stock_reservations.sql:1` — 補上用途註解。\n- 使用者要求寫出取消失敗的具體驗證，不只寫「測試通過」→ 補上 Verification 的操作步驟與觀察結果。\n\n# Unsolved Issues\n\n- [Suggestion] `src/lib/reservations/data.ts:31` — 預留清單每列各查一次可用數量（deferred because: 目前每位業務約 10 筆，排到下一個任務）\n- 缺貨通知與預留自動到期未納入（會議未定案）。\n- 倉管代為取消待 @佩雯 確認；確認後需調整 `cancelReservation` 權限與清單標示。",
  "why": "報告不是對話的替代品；它是可交接的結果。想看當時怎麼討論，還能追到 session log。",
  "routes": [
    "notion",
    "github"
  ],
  "steps": [
    "對照修改與對話",
    "整理結果證據",
    "留下未完成事項"
  ],
  "messages": [
    [
      "user",
      "/report"
    ],
    [
      "skill",
      "/report"
    ],
    [
      "tool",
      "Read · 本輪對話紀錄、實際差異、驗收結果與 REVIEW.md"
    ],
    [
      "assistant",
      "我會把完成的功能、驗證方式、修掉的問題和延後事項分開。報告放在程式所在的 repo，之後才能一起交付。"
    ],
    [
      "artifact",
      "Rename · docs/tasks/庫存預留與取消-3f9a21.md → docs/reports/2026-09-22-庫存預留與取消-3f9a21.md\n保留 # Context，附上 # Plan，再接本輪修改與驗證。"
    ],
    [
      "user",
      "剛剛修的取消失敗也要寫到，不要只寫測試通過。"
    ],
    [
      "assistant",
      "有補上：取消被拒時仍保留原本的預留狀態，之後重新操作也正常。尚未 push 和部署也都有註明。"
    ],
    [
      "artifact",
      "Update · 加入具體重現方式、觀察結果與未測範圍"
    ],
    [
      "assistant",
      "報告已存到 docs/reports/2026-09-22-庫存預留與取消-3f9a21.md，包含本輪修改、驗證結果和延後事項。尚未 push、尚未部署也都有註明；後續修正會接著補在同一份的 Updates。",
      {
        "documents": [
          "report"
        ]
      }
    ]
  ]
};
