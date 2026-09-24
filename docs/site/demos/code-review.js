// Fictional project demonstration. No live tools or external writes.
window.DEV_SKILLS_DEMOS = window.DEV_SKILLS_DEMOS || {};
window.DEV_SKILLS_DEMOS["code-review"] = {
  "id": "code-review",
  "chapter": "check",
  "title": "六位隊友，從不同角度幫你看一輪",
  "intro": "修改一多，光靠一種角度很容易漏看。它會找六個不同分工的 reviewer，分頭看錯誤、規則、歷史、效能、計畫和維護性，再核對證據，把真正值得處理的問題帶回來，讓你決定怎麼修。",
  "input": "本輪修改＋專案規則＋計畫",
  "output": "REVIEW.md",
  "artifact": "---\nreviewed: 2026-09-22T16:40:00+08:00\nbase: main (8e2d4f1)\nhead: 8e2d4f1 + uncommitted working tree (branch feat/stock-reservation)\nscope: this session's reservation work only — product-list edits from another window excluded\nfiles_reviewed_list:\n  - migrations/0012_stock_reservations.sql\n  - src/lib/reservations/actions.ts\n  - src/lib/reservations/data.ts\n  - src/app/(main)/reservations/page.tsx\n  - src/app/(main)/reservations/reserve-button.tsx\nfindings:\n  critical: 0\n  warning: 1\n  suggestion: 1\n  nit: 2\n  total: 4\nstatus: issues_found\nnote_for_next_session: |\n  Reviewed by 6 agents (bugs-security, claude-md, git-history, performance, plan-adherence, quality-architecture).\n  git-history: no regressions of earlier fixes. plan-adherence: 預留、取消、庫存不足、重複送出 all mapped; 缺貨通知 deferred per plan.\n  Fix order: WR-01 first (user-visible state mismatch). SR-01 can wait until the list grows.\n---\n\n# Code Review — 庫存預留與取消\n\n**Status:** issues_found — 4 findings (0 critical, 1 warning, 1 suggestion, 2 nit). One candidate dropped at score 0.\n\n**Files reviewed:** 5\n**Diff range:** `main..working-tree`\n**Intent:** 依計畫實作預留與取消：庫存不足停止預留、同一筆送出只算一次、已出貨不可取消、我的預留清單。缺貨通知與自動到期依計畫不在範圍；商品列表的修改屬於另一個視窗，已排除。\n\n---\n\n## 一眼看懂（現在❌ → 改後✓）\n\n```\nWR-01 取消被拒      ❌ 先把畫面改成「未預留」再送出，被拒也不還原\n                    ✓ 失敗時還原先前狀態，畫面與資料庫一致\nSR-01 清單查詢      ❌ 每一列各查一次可用數量（N 筆 = N 次查詢）\n                    ✓ 一次讀 available_stock，再對應回清單\nNT-01 錯誤訊息      ❌ 「庫存不足」字串在兩個檔案各寫一次\n                    ✓ 集中到 reservations/messages.ts\nNT-02 migration     ❌ 缺少 AGENTS.md 要求的用途註解\n                    ✓ 檔頭補一行用途與對應任務\n```\n\n---\n\n## Bugs & Security\n\n### WR-01 — 取消被拒時，畫面把原本的預留清掉\n\n**Files:** `src/app/(main)/reservations/reserve-button.tsx:44-52`, `src/lib/reservations/actions.ts:71` (`SHIPPED` 分支)\n**Severity:** Warning · **Confidence:** 88\n**Issue:** 按下取消時先 `setStatus(\"none\")` 再呼叫 `cancelReservation`。伺服器對已出貨的預留回傳 `SHIPPED` 時，按鈕沒有還原狀態：畫面顯示「未預留」，資料庫仍是 reserved。業務會以為已取消，再預留一次時可用數量卻沒有加回。\n**Trace:** 取消已出貨的預留 → `cancelReservation` 回 `{ ok: false, code: \"SHIPPED\" }` → 元件忽略回傳值 → 畫面停在未預留。\n**Plan quote:** §7「取消已出貨的預留 → 被拒，畫面保留原本的預留狀態」\n**Fix:**\n```tsx\nconst prev = status;\nsetStatus(\"none\");\nconst res = await cancelReservation(id);\nif (!res.ok) {\n  setStatus(prev);\n  setError(messageFor(res.code));\n}\n```\n\n## Performance\n\n### SR-01 — 預留清單每一列各查一次可用數量\n\n**File:** `src/lib/reservations/data.ts:28-36`\n**Severity:** Suggestion · **Confidence:** 72\n**Issue:** `listReservations` 對每筆預留呼叫一次 `getAvailableQty(product_id)`。目前一位業務約 10 筆預留影響不大，但清單 50 筆就是 50 次查詢，主管檢視全部預留時會更明顯。\n**Fix:** 改讀 `available_stock` view，一次 `where product_id = any($1)` 取回所有商品的可用數量，再對應回清單。\n\n## Quality & Architecture\n\n### NT-01 — 「庫存不足」訊息重複定義\n\n**Files:** `src/app/(main)/reservations/page.tsx:19`, `src/app/(main)/reservations/reserve-button.tsx:12`\n**Severity:** Nit · **Confidence:** 60\n**Issue:** 同一句錯誤訊息在兩個檔案各寫一次，之後改文案容易漏改一處。\n**Fix:** 新增 `src/lib/reservations/messages.ts`，以錯誤碼對應訊息，兩處共用。\n\n## CLAUDE.md Adherence\n\n### NT-02 — migration 缺少用途註解\n\n**File:** `migrations/0012_stock_reservations.sql:1`\n**Severity:** Nit · **Confidence:** 55\n**Issue:** AGENTS.md「每個 migration 檔頭寫一行用途與對應任務」；本檔直接從 `create table` 開始。\n**Fix:** 檔頭補 `-- 庫存預留與取消：預留資料表與 available_stock view（Notion 任務：庫存預留與取消）`。",
  "why": "review 不是六票表決，也不是看到問題就全部自動改。留下證據、修正與延後事項，才接得下去。",
  "routes": [
    "github"
  ],
  "steps": [
    "六種角度",
    "核對證據",
    "選擇修正並複查"
  ],
  "messages": [
    [
      "user",
      "/code-review 只看這次的預留功能修改。"
    ],
    [
      "skill",
      "/code-review"
    ],
    [
      "tool",
      "Scope · 確認本輪範圍，不混入另一個視窗正在改的商品列表"
    ],
    [
      "agent",
      "Bug／安全 · 取消被拒時，畫面把原本的預留狀態清掉了。"
    ],
    [
      "agent",
      "專案規則 · 核對 AGENTS.md：migration 檔頭少了一行用途註解（Nit）。"
    ],
    [
      "agent",
      "歷史脈絡 · 檢查過往修改，沒有把舊問題改回來。"
    ],
    [
      "agent",
      "效能 · 預留清單查詢有重複讀取，附上發生位置與成本依據。"
    ],
    [
      "agent",
      "計畫對照 · 預留、取消與庫存不足限制都有對應；缺貨通知依計畫延後。"
    ],
    [
      "agent",
      "品質／架構 · 「庫存不足」訊息在兩個檔案各寫一次，建議集中（Nit）。"
    ],
    [
      "tool",
      "Review · 逐項核對證據與可信度，寫入 REVIEW.md"
    ],
    [
      "question",
      "找到 4 項：1 Warning、1 Suggestion、2 Nit。怎麼處理？\n全部修｜只修選定項目｜先記入報告"
    ],
    [
      "user",
      "先修取消失敗那個和兩個 Nit。查詢先記下來。"
    ],
    [
      "tool",
      "Edit + Check · 取消被拒時保留原狀態，再測失敗後重新操作"
    ],
    [
      "skill",
      "/code-review · 複查修正"
    ],
    [
      "assistant",
      "REVIEW.md 記下這輪的 4 項發現。取消失敗與兩個 Nit 已修正並複查通過；查詢改善先保留，交接報告也會交代後續處理。",
      {
        "documents": [
          "code-review"
        ]
      }
    ]
  ]
};
