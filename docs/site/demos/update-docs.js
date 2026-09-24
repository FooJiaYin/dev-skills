// Fictional project demonstration. No live tools or external writes.
window.DEV_SKILLS_DEMOS = window.DEV_SKILLS_DEMOS || {};
window.DEV_SKILLS_DEMOS["update-docs"] = {
  "id": "update-docs",
  "chapter": "check",
  "title": "功能變了，文件也別留在昨天",
  "intro": "程式已經改了，文件卻還在說舊做法，下一個人就容易照錯。它會從這次修改找出受影響的文件，先告訴你哪些地方需要更新、為什麼；你確認後，再動手改。",
  "input": "這次程式差異＋專案文件",
  "output": "文件更新預覽",
  "artifact": "Detected docs layout:\n  README.md                  → 功能列表\n  docs/PRD.md                → monolithic\n  docs/specs/預留/features/   → per-feature (1 file)\n\nDiff 分類: schema / service / component\n\nProposed updates:\n  README.md     + 功能列表「庫存預留與取消」（預留頁 /reservations）\n  docs/PRD.md   + 取消規則「已出貨的預留不可由業務自行取消，需走退貨流程」\n                  _(2026-09-22: 依 09/18 會議 五、2.)_\n\nNo change needed:\n  docs/specs/預留/features/預留.md   行為與實作一致（庫存不足停止、同一筆只算一次）\n\nConfirm? [y/n/edit]",
  "why": "先找範圍、列出理由，再改文件。Quick 收尾時只提出建議，不會直接改。",
  "routes": [
    "github"
  ],
  "steps": [
    "偵測文件",
    "列出更新建議",
    "確認後修改"
  ],
  "messages": [
    [
      "user",
      "/update-docs"
    ],
    [
      "skill",
      "/update-docs"
    ],
    [
      "tool",
      "Read · 檢查文件結構與本輪修改"
    ],
    [
      "assistant",
      "找到兩份需要改：README 還沒列預留功能，PRD 的取消規則也少了時間限制。功能規格已經對齊，不用再改一次。"
    ],
    [
      "artifact",
      "Preview · README：補功能入口／PRD：補取消限制"
    ],
    [
      "question",
      "套用這兩項更新嗎？\n全部套用｜只套用部分｜先留建議"
    ],
    [
      "user",
      "兩份都改。"
    ],
    [
      "tool",
      "Edit · README.md、docs/PRD.md"
    ],
    [
      "assistant",
      "文件更新好了。下面這份修改清單可以對照這次調整的內容，接下來也會一起 review，避免程式和文件各說各的。",
      {
        "documents": [
          "update-docs"
        ]
      }
    ]
  ]
};
