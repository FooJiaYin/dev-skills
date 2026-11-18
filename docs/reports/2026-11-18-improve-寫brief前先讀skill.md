# improve：寫 brief 前先讀 skill

來源 session：2026-11-18-1111會議剩餘任務-規格成本-匯率異動-中盒改小盒-報價單圖片字體（b5358f10，專案 sparktoy）。

| 觀察到的摩擦 | 改了什麼 | 檔案 |
|---|---|---|
| 派 agent 同步 Notion 時，brief 為了「不要在共用 dev 上 commit」寫了「截圖不上傳」，蓋掉 `sync-report` 規定的圖片與附件上傳；四張票只有文字，使用者問「為何」才補傳 60 張圖 | 「派 agent 之前」加一條：brief 要 agent 跑某個 skill 時，先自己讀過那個 skill，brief 的限制不得與 skill 衝突；要偏離先問使用者 | `docs/agents-and-sessions.md` |

同一輪另一條（agent 逐檔列測試路徑，含 `[productId]` 的檔被當 glob 漏掉）依使用者指示寫成專案的獨立測試文件 `sparktoy-erp/docs/testing.md`，不放 skill。

沒套用：清 worktree 前先查有沒有腳本或路徑還指著它（使用者沒選）。
