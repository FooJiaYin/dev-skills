---
session: 2026-11-18-報價單-excel-版面-一規格一行-欄寬 (8d6faf78-73f8-4f1f-be84-f6b95d38dcbd)
---

# improve：/verify 沒有 plan 時列出本 session 已做的檢查

## 起因

sparktoy-erp「報價單 Excel 版面」任務沒進 plan mode，`/wrap-up` Full 跑到 `/verify` 時找不到 Test plan，只能停下來問；但同一個 session 已經跑完單元測試、typecheck／lint 與 Google 試算表實拍，使用者回「skip verify」。

## 改動

- `skills/verify/SKILL.md` §1：沒有 plan／Test plan 時仍停下來問，但問題裡要列出本 session 已跑的檢查（指令／情境 → 結果），並提供「以這些為紀錄」或「依任務驗收條件補檢查」兩個選項。
