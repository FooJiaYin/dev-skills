# improve(report, sync-report)：截圖與 artifact 上 Notion

來源 session：2026-11-11-業務報價單-1104回饋（sparktoy，9d5e2527）

## 摩擦

| 發生的事 | 原因 |
|---|---|
| 8 份報價單票的報告同步到 Notion 後沒有任何截圖，使用者兩度要求「sync report should include images / also artifact」 | `/sync-report` 只貼文字；`/report` 沒有截圖放哪裡的規則，截圖留在 scratchpad |
| 一次建 9 個 Notion 上傳網址，再一起 POST，9 個全部 401 過期 | 上傳網址幾分鐘就過期，skill 沒寫 |
| 使用者問「did you run report skill?」：8 個子 agent 照 brief 轉述的步驟寫報告，全都漏了 `attach-plan.sh` | 委派時沒要求子 agent 透過 Skill tool 跑 `/report` |

## 改了什麼

- `skills/sync-report/SKILL.md` 第 8 步後：報告引用的圖片與 `-artifacts/` 裡給人看的檔（截圖、HTML）一併上傳；建上傳網址後同一輪就 POST、一次 ≤3 個；一小時內放到頁面；圖放在 `# Verification` 結尾的 `## 畫面`（`# Result` 之前），HTML 用 `<embed>`；重新 fetch 確認變成 `notion-file-block://`。
- `skills/report/SKILL.md` Pre-flight：委派子 agent 寫逐票報告時，每個 agent 透過 Skill tool 跑 `/report`（與 `/sync-report`），不轉述步驟；驗證截圖複製到 `docs/reports/<report>-artifacts/screenshots/`，在 `# Verification` 結尾 `## 畫面` 引用。
