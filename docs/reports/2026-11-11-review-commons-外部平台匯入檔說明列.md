---
session: 2026-11-04-官網匯入失敗-說明列被當成商品 (0bf8c18b-d874-4b7d-9c94-48b6315cb3f9)
---

# review commons：外部平台匯入檔不得夾帶說明列

# Changes Made

- `shared/review/commons.md` `## Added by /improve` 加一條：上傳到外部平台的檔案（匯入範本、CSV）不得在平台資料範圍內夾帶給人看的說明／範例列；資料起列要對照平台實際讀取起點，並由測試斷言匯出檔不含說明文字。

# Result

- 來源：sparktoy ERP 官網（WACA）首次匯入 3 列全失敗——模板第 3–4 列的「＊如何對應／＊範例」被當成商品讀（修正見 sparktoy-erp PR #12）。原測試只斷言說明列存在，沒有斷言匯出檔不含說明列。
- 同次 /improve 另改了使用者全域 `~/.claude/CLAUDE.md` Background agents 第 10 點（交付檔不放 scratchpad），不在本 repo。
