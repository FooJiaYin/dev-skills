# wrap-up：刪除行也算外來 hunk；scope check 不再假設 HEAD 是自己的

## 摘要

```
現在 ❌                                              改後 ✓
────────────────────────────────────────────────────────────────────────────────
commit.md「確認每個 hunk 都是你的」                   commit.md 追加一段：
  → 只防「別人加的行」混進來                            沒寫過的 `-` 行 ＝ HEAD 比工作區新
  → 工作區落後 HEAD 時，diff 顯示成「我刪了幾行」         （對方 hash-object / commit-tree 提交、沒寫回檔案）
  → 直接 git add ＝ 靜默還原對方的 commit                → 用排序比對 HEAD vs 工作區，每個 `<` 行都要是自己改的

full.md Step 0：git diff --stat HEAD~1..HEAD          改用 commit 訊息 / Session footer 找本 session 的 commit
  → HEAD 是別人疊上來的 commit 時，量到的是別人的 diff
```

# Description

sparktoy-erp 的「收單日期欄位與工作日推算規則」session（`792fdace`）在多 session 並行的 repo 裡跑 `/wrap-up` 時踩到兩個坑：

1. **`AGENTS.md` diff 顯示 `4+/4−`，那 4 行刪除是另一個 session 已提交的通路勾選不變式。** 我的工作區版本落後 HEAD（對方的提交沒回寫到工作區），`git add` 就會把他們的 commit 倒回去。`actions.ts` 同樣少了對方兩行註解，另有一整段被對方搬了位置 —— `git diff` 會把「搬動」顯示成刪除＋新增，只有排序後逐行比對才看得出只是位置不同。當時是靠逐行比對才攔下，commit.md 原本只教「檢查有沒有別人加的行」。
2. **Step 0 的 `git diff --stat HEAD~1..HEAD` 回報「1 file」**，其實是別人疊在我 commit 上的 `7a953fa`，不是我的 14 檔。

根因之一見 `2026-09-16-wrap-up-commit-md-必讀與-session-footer-hook.md`：當天用 `commit-tree` 替 10 筆未推送的 commit 補 Session footer，本 session 的 `33af88e` 被重寫成 `ecd4228`，HEAD 因此比各 session 的工作區認知新。

# Changes Made

| 檔案 | 改動 |
|---|---|
| `skills/wrap-up/commit.md` Smart staging | 新增一段：你沒寫的 `-` 行也是外來的；用 `diff <(git show HEAD:<f> \| sort) <(sort <f>) \| grep '^<'` 檢查，否則以 `git show HEAD:<f>` 為基底重套自己的改動 |
| `skills/wrap-up/full.md` Step 0 | `HEAD~1..HEAD` → 用 commit 訊息 / `Session:` footer（`git log --grep`）找出本 session 的 commit |

同一輪 `/improve` 另寫入全域 `~/.claude/CLAUDE.md`（不在本 repo）：`grep -c` 零筆時 exit 1，會中斷 `&&` 鏈（該 session 發生 4 次）。

# Result

- 兩檔 diff 驗證：`commit.md` 純新增；`full.md` 唯一刪除行為刻意改寫的 Step 0 指令。
- 其他 skill 文件無 `HEAD~1..HEAD` 引用，無連帶漂移。
- 使用者略過的 finding：sync-report 附加回自身任務時 `# Context` 重複、替代審查者需有 Bash、「先引來源文件再看資料」記憶、sparktoy 報告落點。
