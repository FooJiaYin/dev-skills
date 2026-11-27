---
session: 2026-11-27-開課通多租戶架構討論 (79c4ac96-51b8-42f4-a7b4-8081e5b267e1)
---

# Notion 相關 skill：金鑰判斷與報告、計劃的放法

# Description

- 來源：`letsplay-line` 的一場規劃 session（2026-11-27），結尾把會議記錄、討論報告、計劃同步到 Notion 時出了兩類摩擦。使用者指示只更新 Notion 相關的 skill。
- 範圍：`skills/upload-meeting/SKILL.md`、`skills/sync-report/SKILL.md`。

# Changes Made

| 摩擦 | 改了什麼 | 檔案 |
|---|---|---|
| 兩個上傳 agent 只手動看了 Keychain 與環境變數就判斷「沒有 Notion 金鑰」，沒有試跑腳本。金鑰其實在上一層的 `.env`，腳本本來就會往上找。結果整份內容由模型逐段貼上，各跑 39、83 分鐘，逐字稿有 6 個字被自動轉換 | 寫明「沒有金鑰」只能以腳本實際執行的結束代碼 3 為準；派 agent 時要寫進 brief | `upload-meeting` §5、`sync-report` step 8 |
| 走 MCP 路徑時逐字稿只用眼睛核對，同步時間是 agent 自己估的 | MCP 路徑：貼完後用腳本跟原檔比對；`last_synced` 用 `date` 取得；會議頁面只放會議記錄與逐字稿 | `upload-meeting` §5-2 |
| 報告與計劃在 Notion 上怎麼放，使用者改了四次，其中一次 agent 已經把計劃寫進會議頁面，事後要手動刪 | 新增一條：報告放工作項目頁面、計劃放該項目的子頁面；寫入前先用結構圖跟使用者確認 | `sync-report` Notes |

# Result

- 兩個檔各加兩段，沒有改動既有內容。
- 沒有實跑驗證：新增的是給 agent 的指示，這場沒有再跑一次上傳流程。
- `upload-meeting/SKILL.md` 在這次修改前就有另一個 session 未提交的變更（執行環境說明、逐字稿區塊的圍欄寫法），這次的提交只包含上表的兩段。

# Unsolved Issues

- 同一場 session 另外提出、使用者這次沒有選的建議：背景有寫入 agent 時不進 plan mode、提方案前先問會推翻方案的前提、先查第三方條款再建議、轉貼用的訊息寫短版、`report` skill 的計劃附加方式。
