// Fictional project demonstration. No live tools or external writes.
window.DEV_SKILLS_DEMOS = window.DEV_SKILLS_DEMOS || {};
window.DEV_SKILLS_DEMOS["wrap-up"] = {
  "id": "wrap-up",
  "chapter": "check",
  "title": "同樣是收工，趕時間和正式交付都接得住",
  "intro": "功能做完，通常還有驗證、文件、報告和交付要收尾，忙起來很容易漏一步。它會把這些 skills 接成一條流程：Quick 先收好進度，Full 多走品質與交付檢查；需要你決定的地方，仍會停下來問。",
  "input": "今天這個視窗的工作",
  "output": "收尾清單／Quick ＋ Full",
  "artifact": "Quick\n  文件建議（不直接改）→ 報告 → 命名\n  → cleanup + commit → push 選擇\n  → 有設定時回填 Notion → 提醒部署狀態\n  跳過：驗證、review、手動部署、improve\n\nFull\n  驗證 → 文件 → review／修正 → 報告 → 命名\n  → cleanup + commit → push／PR 選擇\n  → Notion → 部署判斷 → improve\n\n兩種都要分清：已 commit ≠ 已 push ≠ 已部署。",
  "why": "有些步驟能串起來，有些決定仍然要問你。網站裡會自動演出回答，真正在工作時仍由使用者確認。",
  "routes": [
    "notion",
    "github"
  ],
  "steps": [
    "選收尾方式",
    "分清自己的修改",
    "交代兩邊進度"
  ],
  "messages": [
    [
      "divider",
      "Quick · 先收好今天的進度"
    ],
    [
      "user",
      "/wrap-up quick"
    ],
    [
      "skill",
      "/wrap-up · Quick"
    ],
    [
      "skill",
      "/update-docs · 只提出建議 → /report → /rename-session"
    ],
    [
      "assistant",
      "今天的修改和報告整理好了。提交範圍只有這個視窗的檔案，別人的修改沒有一起選進來。",
      {
        "documents": [
          "report"
        ]
      }
    ],
    [
      "question",
      "確認提交後，要推到 GitHub 嗎？\n開 PR｜直接 push｜先不 push"
    ],
    [
      "user",
      "先 commit，不 push。"
    ],
    [
      "tool",
      "Git · 建立本地 commit，保留其他視窗的修改"
    ],
    [
      "skill",
      "/sync-report · 有 Notion 設定，接著回填報告"
    ],
    [
      "assistant",
      "Quick 收好了：本地已存成版本、Notion 已更新；沒有 push、沒有部署。這次跳過驗證與 review，之後交付前再補。",
      {
        "documents": [
          "report",
          "sync-report"
        ]
      }
    ],
    [
      "divider",
      "Full · 準備把這一輪交付出去"
    ],
    [
      "user",
      "/wrap-up full"
    ],
    [
      "skill",
      "/wrap-up · Full"
    ],
    ["assistant", "先照 plan.md 驗證這輪修改。測試、文件和 review 會依序接上；中間若要決定取捨，我會停下來問你。"],
    ["skill", "/verify"],
    ["tool", "Test · 取消預留測試失敗：數量沒有釋回"],
    ["assistant", "找到原因了：狀態改成取消後，數量沒有一起更新。我先修正，再重跑相關測試。"],
    ["tool", "Edit · 修正取消後的數量更新"],
    ["tool", "Re-run · 功能測試通過；型別檢查通過；格式檢查通過"],
    ["assistant", "這輪列出的檢查已重跑通過。程式改過了，接著看文件要不要一起校準。"],
    ["skill", "/update-docs"],
    ["tool", "Read · 比對本輪修改與 README、PRD"],
    ["assistant", "兩處需要跟上：README 補功能入口，PRD 補取消限制。其他文件目前與程式一致，不動。"],
    ["question", "這兩處文件更新要套用嗎？\n兩處都套用｜只套用一處｜先留建議"],
    ["user", "兩處都套用。"],
    ["tool", "Edit · 更新 README.md、docs/PRD.md"],
    ["assistant", "文件已更新，修改摘要也留下來了。現在讓六個角度檢查這輪程式與文件。", { "documents": ["update-docs"] }],
    ["skill", "/code-review"],
    ["tool", "Scope · 只檢查這輪修改，不帶進別的視窗正在改的檔案"],
    ["agent", "Bug／安全 · 取消被拒時，畫面把原本的預留狀態清掉了。"],
    ["agent", "專案規則 · migration 檔頭少了用途註解。"],
    ["agent", "歷史脈絡 · 沒有把舊問題改回來。"],
    ["agent", "效能 · 清單查詢有重複讀取，附上位置與成本依據。"],
    ["agent", "計畫對照 · 本輪承諾的情境都有對應；後續功能仍留待下一輪。"],
    ["agent", "品質／架構 · 同一個錯誤訊息寫了兩次，可以集中。"],
    ["tool", "Review · 核對六個角度的證據，整理出 4 項，寫入 REVIEW.md"],
    ["question", "找到 4 項：1 Warning、1 Suggestion、2 Nit。怎麼處理？\n全部修｜只修選定項目｜先記入報告"],
    ["user", "修取消失敗和兩個 Nit，查詢改善先記下來。"],
    ["tool", "Edit + Re-run · 修正後重跑取消情境與相關檢查"],
    ["skill", "/code-review · 複查修正"],
    ["assistant", "已選的三項修正都複查通過；查詢改善附原因留到交接報告。REVIEW.md 裡有每項的證據和去向。", { "documents": ["code-review"] }],
    [
      "skill",
      "/report → /rename-session"
    ],
    [
      "question",
      "報告和這次修改的提交範圍確認好了。怎麼交付？\n開 PR｜直接 push｜先保留本地"
    ],
    [
      "user",
      "開 PR。"
    ],
    [
      "tool",
      "GitHub · 推送本輪工作，建立 Pull Request，附上驗證與未完成事項"
    ],
    [
      "skill",
      "/sync-report"
    ],
    [
      "assistant",
      "Notion 回到同一張任務，狀態先放 Testing，等團隊試用。PR 已開不代表已經部署。",
      {
        "documents": [
          "sync-report"
        ]
      }
    ],
    [
      "question",
      "目前沒有自動部署設定，要現在部署嗎？\n現在處理｜先不要"
    ],
    [
      "user",
      "先不要，等大家看完。"
    ],
    [
      "skill",
      "/improve · 回看這輪有哪些地方值得改進"
    ],
    [
      "assistant",
      "Full 收尾完成：GitHub 有 PR、Notion 有報告與待測項目；部署還沒做，缺貨通知與查詢改善也沒有冒充完成。",
      {
        "documents": [
          "code-review",
          "report",
          "sync-report"
        ]
      }
    ]
  ]
};
