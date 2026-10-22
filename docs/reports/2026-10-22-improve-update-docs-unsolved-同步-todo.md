---
session: 2026-10-22-上架說明套用客戶公版 (36997722-a766-4795-91cc-1172b4e32253)
---

# improve：update-docs 把 Unsolved Issues 逐項同步到 TODO.md

# Description

- sparktoy-erp「上架說明套用客戶公版」wrap-up 後，report 的 Unsolved Issues 只憑記憶抄了部分進 `TODO.md`，漏掉「會議記錄／Notion 仍寫待提供」。使用者：「any unsolved issues should goes to TODO.md」。

# Changes Made

- `skills/update-docs/SKILL.md` step 5：TODO.md 視為文件之一；專案有 `TODO.md`（repo 根或上層）時，逐項 grep `# Unsolved Issues`，缺的補上——follow-up 進未解區、待客戶確認進 Questions。

- `skills/wrap-up/full.md` step 4、`quick.md` step 2：報告寫完後再呼叫一次 `/update-docs`，只處理 `TODO.md`，帶入報告的 `# Unsolved Issues`。update-docs 在 step 2 跑時 review 與報告都還沒產生，完整清單到這裡才有；不調換步驟順序，因為 review 要涵蓋文件修改、報告要記錄文件修改。

# Result

- 下次 update-docs（含 wrap-up 內呼叫）會逐項比對 TODO.md，不再靠記憶。
