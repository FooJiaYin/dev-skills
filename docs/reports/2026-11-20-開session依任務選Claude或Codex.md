---
session: 2026-11-20-開session依任務選Claude或Codex (8ddd5a2c-82ce-4590-91df-939378661335)
commit: c84e9c6
---

# 開 session 依任務類型選 Claude Code 或 Codex

```
現在 ❌                                   改後 ✓
未指定工具 → 沿用目前對話的工具            未指定工具 → 依任務類型選
(Claude 開 Claude、Codex 開 Codex)         ├ 要當場判斷（架構、除錯）→ Claude Code 互動
                                           └ 可排隊（修 bug、補測試、review）
                                               ├ 要本機環境 → Codex 本機 (codex -C)
                                               └ 不用       → Codex 雲端 (codex cloud exec)
                                                              → status/diff → 抽查 → apply
```

# Description

- 起點是使用者問「開出去的 session 是 Claude Code 或 Codex，對雙方溝通有沒有影響」；接著使用者貼了一篇文章的分工建議，要求開 session 時依任務類型選工具。
- Scope：單一主題（開新 session 的工具選擇），寫進 `docs/agents-and-sessions.md` 與 `~/.claude/CLAUDE.md`。

### Goal

- 把「什麼工作交給 Codex、什麼留給 Claude Code」寫成開 session 時會照做的規則。

# 溝通差異：Claude Code vs Codex

使用者：「session 開 claude code / codex，你跟他們溝通會有影響嗎」

回覆重點（依 `docs/agents-and-sessions.md:40-44` 既有規則）：

| 我開的 session | 我能 `SendMessage` 給它嗎 | 怎麼確認它開工了 |
|---|---|---|
| Claude Code | ✓ 出現在 `ListAgents`，雙向傳訊息 | 請它開工前傳訊息報到 |
| Codex | ✗ `ListAgents` 只列 Claude session（未實測） | 只能看檔案：進度檔或它的 session 紀錄 |

- Claude 能在啟動時指定 `-n` 名稱與 `--session-id`；Codex 沒有，要啟動後才拿得到 ID。
- 結論：需要中途來回的工作交給 Claude；範圍清楚、成果寫進檔案的工作交給 Codex 即可。

# 分工建議與 Codex 雲端

使用者貼上 <https://seo.whoops.com.tw/codex-vs-claude-code/> 並寫：
> 開 session 的時候，根據任務類型選擇要開 codex 還是 claude code。把可排隊的批量工作（bug 修復、測試補寫、code review）交給 Codex 的雲端任務。把要當場判斷的探索（架構討論、除錯 session）留給 Claude Code 的互動模式。

本機查證（`codex-cli 0.166.0`）：
- `codex cloud` 有 `exec --env <ENV_ID> [--branch] [--attempts]`、`status`、`list`、`diff`、`apply`。所以雲端任務可以輪詢 status／diff 追進度，不必只靠進度檔。
- `codex cloud list` 回 `No tasks found`：看起來已登入，但沒有 environment／`ENV_ID`。

提出的注意事項：
| 項目 | 問題 |
|---|---|
| 雲端只看得到已 push 的分支 | 未 commit 的改動看不到，要先 push，或改走本機 |
| 很多 bug 修復要在本機重現 | 本機 DB、secrets 在雲端沒有，只能走本機 Codex |
| code review | `quick-review` 審未 commit 的改動，維持本機 `codex review`；雲端只做整條分支的 review |
| 拿回改動 | `apply` 前先讀 diff 抽查 |

# 長短版來回

1. 使用者：「對，不要一長串，給大方向就好，第一句提醒也是」→ 先寫成兩處各一行（CLAUDE.md 一行、agents-and-sessions.md 第 40 行改一句）。
2. 使用者：「套用上述分流規則」→ 我問範圍（部署／分流現有待辦／寫進 skill），使用者答「就你剛剛提議的版本寫進去」→ agents-and-sessions.md 改成完整版（決策樹＋雲端、review、不能互傳訊息三點）；CLAUDE.md 保留一行。

回顧：第 1 點的「不要一長串」原意可能是指回覆太長，我理解成規則要短，多了一輪來回。

# Changes Made

- `docs/agents-and-sessions.md`〈開新 session〉：未指定工具時改為依任務類型選；新增「依任務類型選工具」決策樹與三條註記。同一個 commit 一併收進另一個 Codex session（2026-11-20 21:48，`01a1f937`）未 commit 的三條（Claude/Codex 都可開、Codex 的識別與確認、跨工具交接）：本 session 的改動疊在它上面，拆不開，使用者選擇一起 commit。
- `TODO.md`〈需要人手操作〉加兩條（見下）。
- `~/.claude/CLAUDE.md`〈Background agents〉加一行「開 session 依任務類型選工具」（不在 git 裡）。
- Commit `c84e9c6`：以暫時 index 只寫入上述兩檔，工作區裡其他 session 已 stage／未 stage 的改動都沒帶進去。

# Verification

- 使用者選擇略過 `/verify`、`/update-docs`、`/quick-review`（純文件改動）。
- `git show --stat c84e9c6`：只有 `TODO.md`（+2）與 `docs/agents-and-sessions.md`（+21 −2）；commit 後 `git diff TODO.md` 只剩其他 session 的行。
- 雲端流程沒有實跑：沒有 `ENV_ID`。

# Unsolved Issues

- 2 open items in [TODO.md](../../TODO.md)：Codex 雲端 environment 未設（要連哪些 repo 待定）；暫定由 agent 讀 diff 抽查後才 `apply`，而不是讓 Codex 直接開 PR。

# References

- <https://seo.whoops.com.tw/codex-vs-claude-code/>（使用者提供，未抓取內文）
- `docs/agents-and-sessions.md`〈開新 session〉
- `codex --help`、`codex cloud --help`、`codex cloud exec --help`（codex-cli 0.166.0）
