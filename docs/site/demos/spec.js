// Fictional project demonstration. No live tools or external writes.
window.DEV_SKILLS_DEMOS = window.DEV_SKILLS_DEMOS || {};
window.DEV_SKILLS_DEMOS["spec"] = {
  "id": "spec",
  "chapter": "prepare",
  "title": "把「可以預留」拆成真正能實作的細節",
  "intro": "接下來要把幾句需求拆開：誰能按、庫存不足怎麼辦、取消後看到什麼、資料要留下哪些。文件各有用途，但彼此連得起來。",
  "input": "已確認的預留需求與 PRD",
  "output": "docs/specs/預留/",
  "artifact": "預留/\n  specification.md  整體入口\n  schemas.md        商品與預留資料\n  api.md            預留、取消的請求與回應\n  backend.md        可用數量與權限檢查\n  frontend.md       畫面狀態\n  features/預留.md  各種情境\n\n情境：只剩 1 件，2 人同時送出\n結果：只有 1 人成功，另一人收到庫存不足提示。",
  "why": "把容易漏掉的情境先寫出來，實作和驗收才有同一個依據。小改動不一定需要整套文件。",
  "routes": [
    "github"
  ],
  "steps": [
    "釐清細節",
    "拆成規格",
    "連回驗收"
  ],
  "messages": [
    [
      "user",
      "把預留功能寫成 spec。"
    ],
    [
      "skill",
      "/spec"
    ],
    [
      "tool",
      "Read · PRD 與已確認的方案"
    ],
    [
      "assistant",
      "開始前還有一個缺口：同一個人重複按預留，要重複扣掉庫存嗎？"
    ],
    [
      "user",
      "不行，同一筆需求只能預留一次。"
    ],
    [
      "assistant",
      "收到。我會把成功、庫存不足、重複預留、未登入和取消後再預留都列成情境。沒有決定的缺貨通知則保持待確認。"
    ],
    [
      "artifact",
      "Write · specification.md、schemas.md、api.md、backend.md、frontend.md、features/預留.md"
    ],
    [
      "assistant",
      "規格寫好了。各份文件有互相連結；實作時可以從功能情境追到資料與畫面，不用自己拼。這是規格，還不是已完成的功能。"
    ]
  ]
};
