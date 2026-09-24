// Fictional project demonstration. No live tools or external writes.
window.DEV_SKILLS_DEMOS = window.DEV_SKILLS_DEMOS || {};
window.DEV_SKILLS_DEMOS["fetch-task"] = {
  "id": "fetch-task",
  "chapter": "intake",
  "title": "把任務帶進來，不用再解釋一次背景",
  "intro": "開始做事前，最花時間的常常是重新交代背景。它會把 Notion 任務裡的來源、範圍和方案帶到本地；之後再更新，也只刷新共用背景，不會洗掉你自己的計畫和筆記。",
  "input": "Notion 任務與相關背景",
  "output": "docs/tasks/庫存預留與取消-3f9a21.md",
  "artifact": "---\nnotion:\n  page: https://www.notion.so/zhuoao-demo/庫存預留與取消\n  last_synced: 2026-09-21T09:12:40+08:00\n---\n\n<!-- synced from Notion by /fetch-task · do not edit # Context locally; edits will be lost on refresh -->\n# Context\n## <mention-page url=\"https://www.notion.so/zhuoao-demo/庫存預留與取消討論\"/>\n### 會議記錄 四、庫存預留規則；五、取消預留\n## **四、庫存預留規則**\n### 1. 可用數量與上限\n- **決策**：預留數量不可超過可用庫存；庫存不足時直接停止預留，畫面顯示剩餘數量，不讓業務送出。\n- 預留成功後，可用庫存立即扣掉預留數量，其他業務看到的是扣完後的數字。\n- 可用數量的定義：實際庫存減去所有尚未取消、尚未出貨的預留。\n### 2. 重複送出與同時預留\n- 佩雯擔心網路慢時業務連按兩次，同一筆被記成兩筆預留，事後很難分辨哪一筆是多的。**決策**：同一筆送出只算一次。\n- 志豪提到兩位業務同時搶最後一件時，如果只在畫面上判斷，兩人都會看到「剩 1 件」並送出成功，一樣會超賣。需要在送出的那一刻由系統一起確認庫存，只讓其中一人成功。\n- 具體作法由工程會後提方案，確認後再實作；會中只確定「不能超賣」這個結果。\n### 3. 預留的保留期限\n- 怡君希望預留能保留約三天，讓客人有時間確認；佩雯擔心預留一直不取消會把庫存卡住。\n- 志豪表示自動到期釋放需要排程與通知，工作量不小。**本次未定**，先不做自動到期，列入待定事項。\n---\n## **五、取消預留**\n### 1. 誰可以取消\n- **決策**：業務可以取消自己建立的預留，取消後數量還回可用庫存。\n- 倉管能否代業務取消（例如業務請假、客人直接打給倉庫），佩雯要先問倉庫同事的作業習慣，**本次未定**。\n### 2. 出貨後的限制\n- **決策**：已出貨的預留不可由業務自行取消，需走退貨流程；系統要明確拒絕，不能讓畫面看起來像取消成功。\n- 佩雯補充，退貨流程目前由倉庫人工處理，這次不需要做進系統。\n### 3. 取消紀錄\n- 怡君希望事後能查到是誰、在什麼時候取消了哪一筆預留，避免業務之間的誤會。\n- 志豪表示預留保留狀態（已預留／已取消／已出貨）即可回答這個問題，不需另外做紀錄頁。",
  "why": "背景保持最新，但你自己寫下的計畫、筆記和結果不會被刷新洗掉。",
  "routes": [
    "notion",
    "github"
  ],
  "steps": [
    "Notion 任務",
    "本地工作檔",
    "保留自己的筆記"
  ],
  "messages": [
    [
      "user",
      "/fetch-task",
      {
        "flow": {
          "stage": "fetch-task",
          "state": "working"
        }
      }
    ],
    [
      "skill",
      "/fetch-task"
    ],
    [
      "tool",
      "Notion · 查詢分配給我的進行中任務"
    ],
    [
      "question",
      "這次要接哪一張？\n庫存預留與取消｜商品列表調整"
    ],
    [
      "user",
      "庫存預留與取消。"
    ],
    [
      "tool",
      "Read · 讀取任務完整背景；檢查本地是否已有對應檔案"
    ],
    [
      "artifact",
      "Write · docs/tasks/庫存預留與取消-3f9a21.md",
      {
        "flow": {
          "stage": "fetch-task",
          "state": "done"
        }
      }
    ],
    [
      "assistant",
      "任務已存到 docs/tasks/庫存預留與取消-3f9a21.md，可以直接打開接著看。這一步只讀 Notion，沒有改上面的狀態。",
      {
        "documents": [
          "fetch-task"
        ]
      }
    ],
    [
      "user",
      "之後再拉一次，我自己的筆記會不見嗎？"
    ],
    [
      "assistant",
      "不會。之後只更新 # Context 和同步時間，其他章節原樣保留。你之後自己加的章節也會留著。"
    ]
  ]
};
