---
session: 2026-11-24-spec缺口UI提案-31題定案 (3d519661-3164-4643-8095-6c4ca1fbf647)
---

# improve：sync-report 目標 task 已有報告時先問要不要開 child task

## 摩擦

sontis-ai「正式網站共用外觀」task（3c9d30）已經放了兩份報告（① 盤點定案、②–⑤ 元件），wrap-up 時 `/sync-report` 走 Linked 快速路徑，準備把第三份（spec 缺口 UI 提案 31 題定案）也接在同一張 task 後面。使用者打斷：「41db0e58f56881dfb188dd39183c9d30 有3個report，其中兩個放child task」。結果改成開兩張 child task（`Feature`＝父 task），②–⑤ 從父頁面搬過去、缺口提案放另一張。

## 改動

- `skills/sync-report/SKILL.md` step 3 Linked：目標 task 已經有另一份報告的 body（`# Changes Made`／`# Result`）時，寫入前先 `AskUserQuestion`：接在後面，或開 child task（照 step 5「Create new」只帶屬性建立，`Feature`＝這張 task），並把報告的 `notion.page` 改指向它。

## 這次沒採用的其他建議（使用者選了只做這一條）

- headless-shots：公開 tunnel 的預覽根目錄不准是 worktree（本次照交接單做，`.env` 公開約 3 分鐘）。
- wrap-up commit.md：worktree 隔離的 session 帶 token push 被拒一次就直接給使用者 `!` 指令。
- design：多個 agent 分題畫提案時，brief 列跨題共用用詞表。
