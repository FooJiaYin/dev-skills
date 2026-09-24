// Fictional project demonstration. No live tools or external writes.
window.DEV_SKILLS_DEMOS = window.DEV_SKILLS_DEMOS || {};
window.DEV_SKILLS_DEMOS["spec-review"] = {
  "id": "spec-review",
  "chapter": "prepare",
  "title": "規則改了一句，看看哪些地方要一起跟著改",
  "intro": "後來大家補充：出貨後就不能自己取消。看起來只是一句話，但按鈕、送出時的檢查、錯誤提示和驗收都會受影響。",
  "input": "新增的決定＋既有功能規格",
  "output": "docs/specs/預留/features/預留.md",
  "artifact": "新增決定：出貨後不可自行取消\n\n需要一起更新\n  畫面：取消按鈕改為不可用\n  送出檢查：出貨後拒絕取消\n  提示：說明原因，不只顯示「失敗」\n  驗收：出貨前後各測一次\n\n待確認：倉管同事是否仍能代為取消？",
  "why": "不只改找到的第一段文字，而是沿著使用流程檢查相關地方。",
  "routes": [
    "github"
  ],
  "steps": [
    "讀新決定",
    "逐步對照",
    "確認後更新"
  ],
  "messages": [
    [
      "user",
      "出貨後不能取消，幫我對一下規格。"
    ],
    [
      "skill",
      "/spec-review"
    ],
    [
      "tool",
      "Read · 重新讀取流程、資料定義與相關功能規格"
    ],
    [
      "assistant",
      "找到四處要一起調整：按鈕、送出檢查、提示文字和驗收情境。另外，倉管同事還能幫人取消嗎？這個目前沒有決定。"
    ],
    [
      "user",
      "倉管同事的部分先留問題。其他改。"
    ],
    [
      "artifact",
      "Preview · 本輪只修改取消流程，倉管同事例外保留待確認"
    ],
    [
      "tool",
      "Edit · 更新對應規格，不重寫無關章節"
    ],
    [
      "assistant",
      "四處已對齊。倉管同事的例外還列在待確認，不會默默當成允許，也不會當成禁止。"
    ]
  ]
};
