// Fictional project demonstration. No live tools or external writes.
window.DEV_SKILLS_DEMOS = window.DEV_SKILLS_DEMOS || {};
window.DEV_SKILLS_DEMOS["improve"] = {
  "id": "improve",
  "chapter": "evolve",
  "title": "同一件事，不用下次再提醒一次",
  "intro": "同一個地方每次都要再提醒一次，真的會累。/improve 會回看這輪對話裡的修正，也對照 review 找到的問題，指出卡在哪一步、建議怎麼改。你再決定要不要留下、放在哪裡；確認後才動手，不把一次性的偏好變成所有人的規則。",
  "input": "這輪的卡點與使用者回饋",
  "output": "在對話中提出建議，確認後套用",
  "artifact": "Refinement suggestion 1 — report 的驗證只寫「通過」\n  卡住的步驟：/report 第一版 `# Verification` 只有「測試通過」，使用者要求補上取消失敗的重現方式。\n  建議修改：report skill 的 Verification 規則加一句「每項寫出操作、觀察結果與未測範圍」。\n  範圍：Org（團隊共用）→ dev-skills/skills/report/SKILL.md\n  結果：✓ 已套用\n\nRefinement suggestion 2 — 取消按鈕先改畫面再送出\n  卡住的步驟：/code-review WR-01，伺服器拒絕時畫面沒有還原。\n  建議修改：只影響這個函式，在 `reserve-button.tsx` 的取消處留一行註解。\n  範圍：Code comment（function-local）\n  結果：✓ 已套用\n\nRefinement suggestion 3 — 截圖排列偏好\n  範圍：Skip（使用者選擇略過）",
  "why": "先問這條規則要影響哪裡，再找合適的位置。不是每個小偏好都要變成所有人的規定。",
  "routes": [
    "notion",
    "github"
  ],
  "steps": [
    "找出摩擦",
    "確認適用範圍",
    "修改規則"
  ],
  "messages": [
    [
      "user",
      "/improve"
    ],
    [
      "skill",
      "/improve"
    ],
    [
      "assistant",
      "這輪有三個可以改進的地方：報告寫清楚驗證過程、在取消失敗處加一段提醒，以及截圖排列方式。先看第一項：你希望只用在這個專案，還是整個團隊？"
    ],
    [
      "question",
      "驗證報告的寫法要用在哪裡？\n個人所有工作｜團隊共用｜這個專案｜略過"
    ],
    [
      "user",
      "團隊共用。"
    ],
    [
      "tool",
      "Read · 對照目前 report skill，檢查規則是否已存在"
    ],
    [
      "assistant",
      "如果已經有規定卻沒照做，就先修正執行方式，不再加一條重複的。這裡示範的是還缺這條規則，我會補到報告的驗證要求。"
    ],
    [
      "user",
      "取消失敗留程式註解。截圖那個先不要。"
    ],
    [
      "tool",
      "Edit · 團隊的報告規則＋專案中相關註解；略過截圖偏好"
    ],
    [
      "artifact",
      "改進結果 · 下次報告會要求操作、觀察與未測範圍"
    ],
    [
      "assistant",
      "兩項已處理，截圖規則沒加。修改各自留在所屬的位置，不會把整個團隊綁到某個人的偏好上。"
    ]
  ]
};
