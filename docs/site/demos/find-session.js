// Fictional project demonstration. No live tools or external writes.
window.DEV_SKILLS_DEMOS = window.DEV_SKILLS_DEMOS || {};
window.DEV_SKILLS_DEMOS["find-session"] = {
  "id": "find-session",
  "chapter": "remember",
  "title": "隔天回來：昨天那個決定在哪裡？",
  "intro": "記得聊過，卻忘了在哪個視窗，是很常見的事。你可以用主題、關鍵字或檔案找回相關對話；它也會讀前後文，分清楚當時只是討論，還是真的有做修改。",
  "input": "討論主題、關鍵字或修改過的檔案",
  "output": "~/.claude/projects/zhuoao-erp/demo-0922.log.md",
  "artifact": "# 2026-09-22-庫存預留與取消 · session demo-0922 · ~/zhuoao-erp · feat/stock-reservation\n\n[09-22 09:58 user] /sync\n[09-22 09:58 skill] sync\n[09-22 10:00 assistant] ✓ 同步完成。你在 branch: feat/stock-reservation；已併入 main 與 feat/product-list；工作目錄乾淨，可以開工。\n[09-22 10:02 user] /fetch-task\n[09-22 10:03 skill] fetch-task\n[09-22 10:03 ask] 這次要接哪一張？ → 庫存預留與取消\n[09-22 10:05 write] docs/tasks/庫存預留與取消-3f9a21.md tool=Write\n[09-22 10:06 assistant] 任務已存到 docs/tasks/庫存預留與取消-3f9a21.md。Context 來自 09/18 會議四、五章；這一步只讀 Notion，沒有改狀態。\n[09-22 10:12 user] 照 docs/plans/2026-09-21-庫存預留與取消.md 開始做，先做 migration 和 server action。\n[09-22 10:18 user] 出貨後就不能讓業務自己取消，要走退貨，跟會議說的一樣。\n[09-22 10:19 note] 已決定：出貨後不可自行取消，回傳 SHIPPED（會議 五、2.）\n[09-22 10:20 assistant] 好。cancelReservation 會先檢查狀態：已出貨回 SHIPPED，畫面維持已預留，不會看起來像取消成功。\n[09-22 11:40 write] migrations/0012_stock_reservations.sql tool=Write\n[09-22 11:52 write] src/lib/reservations/actions.ts tool=Write\n[09-22 12:05 write] src/lib/reservations/data.ts tool=Write\n[09-22 13:30 write] src/app/(main)/reservations/page.tsx tool=Write\n[09-22 13:30 write] src/app/(main)/reservations/reserve-button.tsx tool=Write\n[09-22 14:12 error] yarn test reservations — cancel after shipped: expected SHIPPED, received OK\n[09-22 14:15 assistant] 狀態判斷寫在更新之後，所以已出貨也被改成 cancelled。改成先檢查狀態再更新。\n[09-22 14:20 write] src/lib/reservations/actions.ts tool=Edit\n[09-22 14:24 assistant] yarn test reservations 9 項全過；併發測試兩人搶最後一件，1 筆成功、1 筆 INSUFFICIENT_STOCK。\n[09-22 15:03 user] 倉管能不能幫業務取消？先不要做，等佩雯問完。\n[09-22 15:04 note] 待確認：倉管代為取消（@佩雯），本輪不實作\n[09-22 16:30 user] /update-docs\n[09-22 16:33 write] README.md tool=Edit\n[09-22 16:33 write] docs/PRD.md tool=Edit\n[09-22 16:35 user] /code-review 只看這次的預留功能修改。\n[09-22 16:35 skill] code-review\n[09-22 16:44 write] REVIEW.md tool=Write\n[09-22 16:45 assistant] 找到 4 項：WR-01 取消被拒時畫面清掉原本的預留、SR-01 清單查詢、兩個 Nit。\n[09-22 16:52 user] 先修取消失敗那個和兩個 Nit。查詢先記下來。\n[09-22 16:58 write] src/app/(main)/reservations/reserve-button.tsx tool=Edit\n[09-22 16:59 write] src/lib/reservations/messages.ts tool=Write\n[09-22 16:59 write] migrations/0012_stock_reservations.sql tool=Edit\n[09-22 17:01 note] 驗證通過：取消被拒時保留原本的預留狀態（WR-01 複查）\n[09-22 17:02 user] /report\n[09-22 17:05 write] docs/reports/2026-09-22-庫存預留與取消-3f9a21.md tool=Write\n[09-22 17:07 user] 剛剛修的取消失敗也要寫到，不要只寫測試通過。\n[09-22 17:08 write] docs/reports/2026-09-22-庫存預留與取消-3f9a21.md tool=Edit",
  "why": "找到提過某個檔案的對話，不代表那個視窗真的改過它。查修改歸屬時，要看實際寫入紀錄。",
  "routes": [
    "notion",
    "github"
  ],
  "steps": [
    "主題或檔案搜尋",
    "讀回前後脈絡",
    "接著工作"
  ],
  "messages": [
    [
      "user",
      "/find-session 取消預留"
    ],
    [
      "skill",
      "/find-session"
    ],
    [
      "tool",
      "Search · 先查目前專案，搜尋主題「取消預留」"
    ],
    [
      "assistant",
      "找到「庫存預留與取消」。我先讀那一段前後內容，確認不是只提到相同關鍵字。"
    ],
    [
      "tool",
      "Read · 對話中的方案、你的選擇與後續結果"
    ],
    [
      "assistant",
      "昨天選的是：出貨後不能自行取消。倉管同事能不能代取消還沒決定，並沒有被當成已做。"
    ],
    [
      "user",
      "那個失敗後畫面清空，也是這個視窗修的嗎？"
    ],
    [
      "tool",
      "Search · 以預留頁檔案查實際寫入紀錄"
    ],
    [
      "assistant",
      "是，這段示範紀錄有對應修改和複查結果。若只有討論、沒有寫入證據，我會分開說，不靠提到檔名就認領。",
      {
        "documents": [
          "find-session"
        ]
      }
    ]
  ]
};
