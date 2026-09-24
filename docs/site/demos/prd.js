// Fictional project demonstration. No live tools or external writes.
window.DEV_SKILLS_DEMOS = window.DEV_SKILLS_DEMOS || {};
window.DEV_SKILLS_DEMOS["prd"] = {
  "id": "prd",
  "chapter": "prepare",
  "title": "文件散在好幾處，先拼回同一個故事",
  "intro": "網站已經有商品列表、員工登入和一些會議記錄。當大家開始各自記得不同版本，就可以把現行需求整理成共同參考，不用每次翻遍聊天。",
  "input": "會議、任務、既有規格與實際頁面",
  "output": "docs/PRD.md",
  "artifact": "# 琢奧 ERP\n\n## 目的\n讓業務同事自己預留，也讓倉管同事掌握預留清單。\n\n## 現有頁面\n商品列表、員工登入\n\n## 本輪新增\n預留、取消、可用數量顯示\n\n## 尚未決定\n缺貨通知\n\n每個決定附回來源；已實作與待做分開。",
  "why": "PRD 是把已有的資料整合起來，不是在資料不足時替團隊發明需求。",
  "routes": [
    "notion",
    "github"
  ],
  "steps": [
    "盤點來源",
    "核對現況",
    "整合共同參考"
  ],
  "messages": [
    [
      "user",
      "文件散了，幫我整理成一份 PRD。"
    ],
    [
      "skill",
      "/prd"
    ],
    [
      "tool",
      "Read · 會議記錄、任務、設計文件；核對目前網站頁面"
    ],
    [
      "assistant",
      "兩份舊記錄有一個差異：早期說預留後不能取消，最新會議改成可以取消。以最新決議為準嗎？"
    ],
    [
      "user",
      "對，舊版留個註記就好。"
    ],
    [
      "assistant",
      "好。我會把已經有的商品列表與登入，和這輪要新增的預留分開。缺貨通知還沒決定，不會寫成一定要做。"
    ],
    [
      "artifact",
      "Write · docs/PRD.md\n流程、頁面、權限與決策來源整理在一起。"
    ],
    [
      "assistant",
      "整理好了。讀者可以先看現在怎麼運作，再追到每個決定的來源，不需要猜哪份文件比較新。"
    ]
  ]
};
