# improve：任務章節順序、agent 實測前置、接手時對照會議

來源 session：2026-11-18-1111會議剩餘任務-規格成本-匯率異動-中盒改小盒-報價單圖片字體（b5358f10，專案 sparktoy）。

| 觀察到的摩擦 | 改了什麼 | 檔案 |
|---|---|---|
| 把客戶範本掛到 Notion 任務時，被更正三次：檔案／連結分開放、Reference 要在最後、客戶的 Google 試算表範本也算 Resource | 守則加一條：章節順序 Context → Resource → Plan → … → Updates → … → Reference；Resource＝任務素材，Reference＝工作指向的東西 | `skills/sync-report/SKILL.md` |
| 三個 subagent 在 auto mode 分別被擋（補 `node_modules` 套件、存測試商品、起 dev server），都是做到一半才發現；主對話還下過前後矛盾的寫入指示 | 「派 agent 之前」加一條：瀏覽器實測的前置（套件齊全、dev server、可寫哪些測試資料）由主對話做完再派 | `docs/agents-and-sessions.md` |
| 交接檔把一張票整張列為等外部資料，其實四項有兩項不用等；沿用的分支只做了成本的人工覆寫，會議 Action Item 寫的是售價 | `start` 加一段：接手交接檔或既有分支也要對照會議 Action Items；「等外部資料」拆到子項 | `skills/align/SKILL.md` |

沒套用：review 共用規則（改寫幣別要同時換算、伺服端計算不可依賴權限過濾後的值）——使用者沒有選。

未做：`skills/report/SKILL.md` 的「Final section order」與 `skills/fetch-task/SKILL.md` 還沒寫進 Resource／Reference 的位置，因為這兩個檔當時有別的 session 已暫存、未 commit 的改動。
