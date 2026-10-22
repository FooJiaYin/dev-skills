---
session: 2026-10-22-上架說明套用客戶公版 (36997722-a766-4795-91cc-1172b4e32253)
---

# improve：commit --mine 誤歸屬、headless 存檔時序

# Description

- 來源：sparktoy-erp「上架說明套用客戶公版」session 的 wrap-up。

# Changes Made

- `skills/wrap-up/commit.md`：`--mine --stage` 報衝突時，session log 可能過度歸屬（本 session 第一個唯讀 Bash 被記成 68 次寫入，AGENTS.md 因此衝突）。遇到不記得自己寫過的 hunk，以自己的 diff 為準，改走「HEAD＋自己的段落」手動路徑。
- `skills/headless-shots/SKILL.md`：每次存檔後等按鈕恢復可按、狀態訊息真的改變才做下一步；按到仍 disabled 的按鈕會被靜默忽略，畫面還留著上一則「已儲存」。每筆寫入用 SQL 確認。
- （本機 `~/.claude/CLAUDE.md`，不在本 repo）第一次改程式前先確認分支與其他 session。

# Result

- 兩個 skill 檔各加一句。session-log 歸屬本身的 bug 未修，只在 commit.md 留下處理方式。
