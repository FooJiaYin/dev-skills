// Fictional project demonstration. No live tools or external writes.
window.DEV_SKILLS_DEMOS = window.DEV_SKILLS_DEMOS || {};
window.DEV_SKILLS_DEMOS["setup-notion"] = {
  "id": "setup-notion",
  "chapter": "intake",
  "title": "先認一下：團隊把任務放在哪裡？",
  "intro": "每次都要告訴 AI「任務放這裡、會議放那裡」，其實很容易貼錯。先把團隊共用的 Notion 位置設定好，之後整理會議、接任務和回填結果，就有同一份設定可以照著走。",
  "input": "團隊的 Notion 任務庫、會議庫",
  "output": "AGENTS.md",
  "artifact": "## Notion\n\nRoadmap (tasks): https://www.notion.so/zhuoao-demo/Roadmap?v=current\nMeetings: https://www.notion.so/zhuoao-demo/Meetings?v=all\nMeetings title format: `<mention-date start=\"<date>\"/> <topic>`\nProject (ERP): https://www.notion.so/zhuoao-demo/ERP\n\n### Team\n\n- 志豪 <zhihao@example.com> — notion-user-demo-1 (member)\n- 怡君 <yijun@example.com> — notion-user-demo-2 (guest)\n- 佩雯 <peiwen@example.com> — notion-user-demo-3 (guest)",
  "why": "先確認目的地，再開始寫入。個人的身分設定不混進團隊共用檔。",
  "routes": [
    "notion"
  ],
  "steps": [
    "確認位置",
    "檢查可讀取",
    "留下共用設定"
  ],
  "messages": [
    [
      "user",
      "/setup-notion"
    ],
    [
      "skill",
      "/setup-notion"
    ],
    [
      "tool",
      "Read · 檢查專案與上層資料夾的 AGENTS.md、.gitignore"
    ],
    [
      "assistant",
      "這個專案還沒有 Notion 設定，不過上層已經有團隊的任務庫與會議庫。要沿用嗎？"
    ],
    [
      "question",
      "沿用上層設定？\n沿用｜另外提供"
    ],
    [
      "user",
      "沿用，這是同一個團隊。"
    ],
    [
      "tool",
      "Read · 確認任務庫與會議庫可以讀取"
    ],
    [
      "artifact",
      "Edit · AGENTS.md、.gitignore\n保留其他規則，只補缺少的設定。"
    ],
    [
      "assistant",
      "設定好了。接下來上傳會議、拉任務和回填結果，都會使用這組位置；這一步還沒有改任何 Notion 內容。",
      {
        "documents": [
          "setup-notion"
        ]
      }
    ]
  ]
};
