// Fictional project demonstration. No live tools or external writes.
window.DEV_SKILLS_DEMOS = window.DEV_SKILLS_DEMOS || {};
window.DEV_SKILLS_DEMOS["rename-session"] = {
  "id": "rename-session",
  "chapter": "handoff",
  "title": "下次找它時，不用猜哪個視窗才是",
  "intro": "開了幾個視窗之後，一排「New conversation」真的很難認。它會用這輪工作的主題替對話命名，讓你下次比較容易找到；只改名稱，不改寫原本的對話。",
  "input": "報告的日期與主題",
  "output": "Session／庫存預留與取消",
  "artifact": "原本\n  New conversation\n\n改成\n  庫存預留與取消\n\n報告與 session 使用一致的主題。\n只調整名稱，不改寫對話內容。",
  "why": "一個小小的名稱，也能省掉之後找半天的時間。命名和原始紀錄各做各的事。",
  "routes": [
    "github"
  ],
  "steps": [
    "取報告主題",
    "使用工具對應的命名方式",
    "核對名稱"
  ],
  "messages": [
    [
      "user",
      "/rename-session 庫存預留與取消"
    ],
    [
      "skill",
      "/rename-session · 庫存預留與取消"
    ],
    [
      "tool",
      "Read · 使用本輪報告的日期與主題，確認目前 session"
    ],
    [
      "assistant",
      "我把這個視窗改成「庫存預留與取消」，和報告的主題對齊。"
    ],
    [
      "tool",
      "Session · 透過目前工具支援的方式更新名稱"
    ],
    [
      "artifact",
      "Session title · 庫存預留與取消"
    ],
    [
      "assistant",
      "名稱更新好了。下次可以直接認標題；如果記得的是某個檔案或討論內容，也可以用 /find-session 找。"
    ]
  ]
};
