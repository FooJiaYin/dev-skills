// Fictional project demonstration. No live tools or external writes.
window.DEV_SKILLS_DEMOS = window.DEV_SKILLS_DEMOS || {};
window.DEV_SKILLS_DEMOS["create-tasks"] = {
  "id": "create-tasks",
  "chapter": "intake",
  "title": "有些要新做，有些其實已經在做了",
  "intro": "會議裡提到的事，不一定都要新開任務，有些可能已經有人在做。它會先比對現有工作，整理出新建、連回原任務和暫時略過的清單；你確認後，才真正寫入。",
  "input": "會議記錄＋目前的 Notion 任務",
  "output": "docs/tasks/_plan-2026-09-18-庫存預留與取消討論.md",
  "artifact": "# /create-tasks 計畫 — 2026-09-18 庫存預留與取消討論\n\n**3 項 · 1 create · 1 link · 1 skip · 1 前置上傳**\n\n## 摘要（先看這張圖）\n\n| # | 會議承諾（Action Items） | 對照 Roadmap Current view（2026-09-18 實查） | 處置 |\n|---|---|---|---|\n| 1 | 實作預留與取消，含庫存不足停止預留與重複送出處理 | 無相符任務；「商品列表調整」是另一件事，不合併 | **B1 CREATE** |\n| 2 | 員工登入補上業務與倉管角色 | 「員工登入」In Progress · @志豪 ⇒ 同一件事的延伸 | **C1 LINK** |\n| 3 | 整理缺貨通知的使用情境 | 會中未定案（八、尚未定案事項） | **SKIP** |\n| 八 | 倉管代為取消、預留保留期限 | 待確認事項，非承諾 | **SKIP**（折入 B1 Context） |\n\n執行順序（照序，否則 mention 錨點抓不到）：\n\n```\nA1 上傳會議到 Notion ──→ 取得 meeting-url\n        │\n        ├─→ B1 create-pages（帶 Discussions:[meeting-url]，Tasks 關聯自動鏡像）\n        ├─→ C1 /fetch-task → # Context 追加\n        ├─→ notion-fetch 會議頁 → 兩個 Action Item 錨點加 <mention-page>\n        └─→ SQL read-back 驗新列的 Name/Status/Type/Time/Assignee\n```\n\n<!-- schema-cache（2026-09-18 以 SQL 實查）\n[🏗️ Tasks]\nName: title\nType: select(Feature ⛰️|Task 🔨|Bug 🐞|Survey 🔍|Test 🧪|Documentation 📄)\nStatus: status(to_do:Not Started | in_progress:In Progress,Testing | complete:Completed 🙌)\nPriority: select(P1 🔥|P2|P3)\nAssignee: person\nTime: date\nDiscussions: relation→Meetings\n-->\n\n---\n\n## A. 前置（核准後第一步）\n\n### A1. 上傳會議記錄到 Notion ✅\n**UPLOAD** → 會議記錄 DB\n- 檔案：`docs/meetings/2026-09-18-庫存預留與取消討論.md`\n- 名稱：`<mention-date start=\"2026-09-18\"/> 庫存預留與取消討論`\n- 日期 `2026-09-18` · 參與人留空（使用者選擇）\n- 上傳後回寫本機檔 `notion.page` frontmatter（`/upload-meeting` 自己做）\n\n---\n\n## B. 新建任務\n\n### B1. 庫存預留與取消 ✅\n**CREATE** · Feature ⛰️ · @志豪 · Priority P1 🔥 · Time: 2026-09-25\n- 來源承諾：@志豪「實作預留與取消，含庫存不足停止預留與重複送出處理」\n- 相關章節：「四、庫存預留規則」全段；「五、取消預留」全段；「八、尚未定案事項」的倉管代取消、保留期限\n- Body: `# Context`（四、五章原文）＋ `# Plan`（使用者要求：選定方案完整保留，不只留摘要）\n- 標註錨點：`實作預留與取消`\n\n```\n四、庫存預留規則\n1. 可用數量與上限\n- 決策：預留數量不可超過可用庫存；庫存不足時直接停止預留，畫面顯示剩餘數量，不讓業務送出。\n2. 重複送出與同時預留\n- 決策：同一筆送出只算一次。\n- 需要在送出的那一刻由系統一起確認庫存，只讓其中一人成功。\n3. 預留的保留期限\n- 本次未定，先不做自動到期。\n---\n五、取消預留\n1. 誰可以取消\n- 決策：業務可以取消自己建立的預留，取消後數量還回可用庫存。\n2. 出貨後的限制\n- 決策：已出貨的預留不可由業務自行取消，需走退貨流程。\n```\n\n---\n\n## C. 追加到既有任務（只寫 `# Context`，不動任何屬性）\n\n### C1. 取消權限需要的角色 ✅\n**LINK** → 員工登入 · In Progress · @志豪\n- 對應承諾：@志豪「員工登入補上業務與倉管角色，供取消權限判斷」\n- 現況：既有任務只處理登入與 `role = admin | sales`；倉管角色不存在\n- 追加內容：「五、取消預留／1. 誰可以取消」\n- 標註錨點：`員工登入補上業務與倉管角色`\n\n---\n\n## D. 跳過\n\n| # | 項目 | 原因 |\n|---|---|---|\n| D1 | @怡君 整理缺貨通知的使用情境 | 會中未定案，列在「八、尚未定案事項」；情境整理好後可 `promote skip-D1 to draft` |\n| D2 | 倉管能否代為取消 | 非承諾，是待確認事項；折入 B1 的 Context，確認後再調整 B1 |\n| D3 | 預留保留期限 | 會中明確「這次先不要」；折入 B1 的 Context |\n\n---\n\n## 執行紀錄\n\n已核准並寫入 Notion：會議已上傳；新建「庫存預留與取消」、既有「員工登入」追加 `# Context`，原本的計畫與屬性未變動。會議頁 `Tasks` 已關聯兩張任務，會議內文的兩個承諾已改為任務 mention。缺貨通知沒有建立任務。SQL read-back：B1 的 Name／Status（Not Started）／Type／Time／Assignee 皆正確。",
  "why": "任務要帶得走原意，也要避免重複。摘要可以幫忙閱讀，但不能取代已經確認的方案。",
  "routes": [
    "notion"
  ],
  "steps": [
    "比對既有任務",
    "預覽與調整",
    "核准後建立"
  ],
  "messages": [
    [
      "user",
      "/create-tasks 從剛才的會議建立任務。",
      {
        "flow": {
          "stage": "create-tasks",
          "state": "working"
        }
      }
    ],
    [
      "skill",
      "/create-tasks"
    ],
    [
      "tool",
      "Notion · 讀取會議、任務欄位與目前進行中的項目"
    ],
    [
      "assistant",
      "找到三項。預留與取消需要新建；登入已經有任務，我會連回去；缺貨通知還沒定，先略過。每項都附上原本討論的背景。"
    ],
    [
      "artifact",
      "Preview · 1 項新建／1 項連結／1 項略過",
      {
        "flow": {
          "stage": "create-tasks",
          "state": "preview"
        }
      }
    ],
    [
      "user",
      "預留那張記得保留剛剛選定的方案，不要只剩摘要。"
    ],
    [
      "assistant",
      "任務預覽已整理好，選定方案也完整保留了。既有的登入任務只補 # Context，不改原本的計畫。你確認這份清單後，我才寫入 Notion。",
      {
        "documents": [
          "create-tasks"
        ]
      }
    ],
    [
      "question",
      "這兩項可以寫入嗎？\n核准｜繼續調整"
    ],
    [
      "user",
      "核准。"
    ],
    [
      "tool",
      "Notion · 建立預留任務、補入登入任務背景，連回會議",
      {
        "flow": {
          "stage": "create-tasks",
          "state": "done"
        }
      }
    ],
    [
      "assistant",
      "處理好了：已在 Notion 新建「庫存預留與取消」，也把這次討論連回既有的「員工登入」任務。兩項都已連回來源會議。任務建立紀錄裡有核准的清單與寫入結果；缺貨通知沒有建立。",
      {
        "documents": [
          "create-tasks"
        ]
      }
    ]
  ],
  "previewArtifact": "待確認的任務清單\n\n新建：庫存預留與取消\n連回既有任務：員工登入\n略過：缺貨通知\n\n尚未寫入 Notion，等待使用者核准。"
};
