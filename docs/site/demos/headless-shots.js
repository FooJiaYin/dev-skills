// Fictional project demonstration. No live tools or external writes.
window.DEV_SKILLS_DEMOS = window.DEV_SKILLS_DEMOS || {};
window.DEV_SKILLS_DEMOS["headless-shots"] = {
  "id": "headless-shots",
  "chapter": "check",
  "title": "真的按一次，不是只看畫面有出來",
  "intro": "預留頁做好了，先當一次業務同事：預留、重新整理、取消，再換倉管同事的身分看預留清單。畫面說成功，資料也要真的有留下來。",
  "input": "本地預留頁＋測試帳號",
  "output": "驗證紀錄／預留操作",
  "artifact": "操作                  畫面與資料\n業務同事按預留          顯示成功；新增一筆\n重新整理              仍顯示已預留\n重複送出              沒有新增第二筆\n取消預留              釋出 1 件庫存\n另一位業務同事查看      看不到其他部門的預留資料\n倉管同事查看            看得到庫存預留清單\n\n這裡是虛構測試結果，並非連線到真實網站。",
  "why": "看得到頁面，只能證明頁面開得起來；真的填寫、存檔並核對資料，才知道這條路走不走得通。",
  "routes": [
    "github"
  ],
  "steps": [
    "操作畫面",
    "檢查資料",
    "留下證據"
  ],
  "messages": [
    [
      "user",
      "幫我真的走一次預留流程。"
    ],
    [
      "skill",
      "/headless-shots"
    ],
    [
      "tool",
      "Browser · 開啟本地頁面，使用測試帳號，不拿真人的登入資料"
    ],
    [
      "assistant",
      "先用業務同事身分預留，再重新整理確認。接著測取消和重複送出，最後換倉管同事看預留清單。"
    ],
    [
      "tool",
      "Browser · 預留 → 重新整理 → 再按預留 → 取消"
    ],
    [
      "tool",
      "資料核對 · 成功時新增一筆；重複送出不新增；取消後可用數量釋出"
    ],
    [
      "assistant",
      "這幾個流程都符合預期。也確認業務同事看不到其他部門的預留資料。"
    ],
    [
      "artifact",
      "Screenshot · 預留成功、取消後、倉管檢視畫面"
    ],
    [
      "assistant",
      "截圖與核對結果都留下了。這次是在本地測試，不能因此說正式網站也已經更新。"
    ]
  ]
};
