// Fictional project demonstration. No live tools or external writes.
window.DEV_SKILLS_DEMOS = window.DEV_SKILLS_DEMOS || {};
window.DEV_SKILLS_DEMOS["verify"] = {
  "id": "verify",
  "chapter": "check",
  "title": "跑過、修好，再跑到通過",
  "intro": "第一次測試沒過，不是交差的時候。它會照原本的測試計畫執行，遇到失敗就找原因、修正，再重跑確認，直到這輪測試通過。若被環境或缺少的設定擋住，也會說清楚，不把沒跑完當作成功。",
  "input": "既有的測試計畫與本輪修改",
  "output": "對話中的測試、修正與重跑結果，不另外產出清單",
  "artifact": "測試執行示範（不是產出的文件）\n\n第一輪：取消預留測試失敗\n修正：取消後釋出對應數量\n第二輪：功能測試通過，型別檢查失敗\n修正：補齊回傳結果的型別\n第三輪：重跑相關測試、型別與格式檢查，全數通過\n\n所有結果皆為虛構示範。",
  "why": "測試通過要靠實際重跑確認，不是把錯誤列出來就結束；外部阻礙也要交代清楚。",
  "routes": [
    "github"
  ],
  "steps": [
    "照計畫跑測試",
    "失敗就修正",
    "重跑直到通過"
  ],
  "messages": [
    [
      "user",
      "/verify"
    ],
    [
      "skill",
      "/verify"
    ],
    [
      "tool",
      "Read · plan.md 的測試計畫與本輪修改"
    ],
    [
      "assistant",
      "先跑計畫裡的預留、取消和重複送出測試，再檢查型別與格式。有失敗就修正後重跑。"
    ],
    [
      "tool",
      "Test · 取消預留失敗：預期釋出 2 件，實際仍保留 2 件"
    ],
    [
      "assistant",
      "取消狀態改了，但對應數量沒有釋出。我會修正這段，再重跑取消和重複取消測試。"
    ],
    [
      "tool",
      "Edit · 修正取消後的數量更新"
    ],
    [
      "tool",
      "Test · 預留、取消、重複取消、重複送出：全部通過"
    ],
    [
      "tool",
      "Type check · 失敗：取消結果的回傳型別缺少 releasedQuantity"
    ],
    [
      "assistant",
      "功能測試過了，型別檢查還沒過。補齊回傳型別後，再一起重跑。"
    ],
    [
      "tool",
      "Edit · 補齊取消結果的回傳型別"
    ],
    [
      "tool",
      "Re-run · 功能測試通過；型別檢查通過；格式檢查通過"
    ],
    [
      "assistant",
      "這輪測試通過了。修正了取消後沒有釋出數量，以及回傳型別缺漏；相關測試、型別與格式檢查都已重跑確認。這裡是本機驗證結果，不代表已部署。"
    ]
  ]
};
