---
session: 2026-10-14-官網原型-V1-V6-V7 (8c2d213b-cfef-4ca0-b8f1-0d61b23a73ed)
---

# improve：新增 explore、headless-shots 步驟截圖、sync-report 404 診斷

# Description

- 來源：人生單向列車官網原型 session（做多個設計版本給使用者挑選，再完成其中三版）中的摩擦。

# Changes Made

| 摩擦 | 修改 |
|---|---|
| 使用者要「3個版本給我選」，只換了風格、排版相同，被追問「排版也有差異」 | 新增 `skills/explore/SKILL.md`：先定差異軸（預設排版＋呈現＋風格都要不同）、只做最能看出差異的段落、每版桌機／手機截圖、發布同一個預覽連結、每輪一張比較表、選定後封存其餘 |
| Claude in Chrome 視窗卡在 606px 無法調整；headless-shots 沒有「捲動／滑鼠後截視窗」，臨時寫了腳本 | 新增 `skills/headless-shots/scripts/steps.mjs`（步驟 JSON：js／mouse／wait／shot、可設寬高與手機觸控、所有結束路徑都關 Chrome），SKILL.md 加一節用法 |
| `/sync-report` 抓 Roadmap 回 404，實際是 Notion 連線登入在別的 workspace，多查一輪才知道 | `skills/sync-report/SKILL.md` 步驟 1：404／object_not_found 時立即 `notion-get-self` 告知 workspace，請使用者用 `/mcp` 重連後再跑 |

# Verification

- `steps.mjs` 的內容來自該 session 實際使用過數十次的 `shots.mjs`（桌機 1440×900、手機 390×844，含捲動與 hover），只加上關閉 Chrome 的 exit hook 與 `CHROME` 變數；改寫後未再實跑。

# Result

- 三項修改都是加法；README 的技能清單未加入 explore（README 有其他 session 未提交的修改，避免混在一起）。
