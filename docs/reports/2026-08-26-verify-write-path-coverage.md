# verify skill：要求每條寫入路徑都有一次 round-trip

# Description

- 在 sparktoy-erp 產品建檔 session 中，測試計畫只走了 create/import/read，`updateProduct` 從未被執行，直到 advisor 指出才補測（並因此發現一個資料遺失 bug）。由 `/improve` 提出、用戶核可，把「寫入路徑覆蓋檢查」寫進 verify skill。

# Changes Made

- `skills/verify/SKILL.md` Guardrails 新增一條：回報完成前先列出本次改動引入的每條寫入路徑（create/update/archive/delete/import…），確認各有一次實際 round-trip；只走 create 的測試計畫視為不完整，要點名缺的路徑而非宣告 pass。
- 同輪另外落地（非 skill）：`~/.claude/CLAUDE.md` Node.js 段補三條機器環境規則（nvm/brew PATH、`yarn add` 交給用戶跑、先查 `lsof -i :3000` 重用 dev server）；`sparktoy-erp/AGENTS.md` 新建（投影範圍寫入規則、名詞表、disabled 樣式）。

Result: Success — 純文字編輯。

# Result

- 無測試可跑。dev-skills 工作樹另有其他 session 未提交的 skill 改動（create-tasks / fetch-task / report / sync-report / find-session），本次只動 `skills/verify/SKILL.md`，提交時請單獨 stage。
