---
session: 2026-09-19-琢奧AI專案橫向比較與dodo升級討論 (6f6767be-df03-428d-8adf-d635a7d51aa8)
---

# improve：require-session-footer 誤擋與漏擋修正

# Description

- `bin/require-session-footer.py`（PreToolUse hook，擋下缺 `Session:` 頁尾的 commit）在一次跨專案盤點的 session 裡出現三個問題，由 `/improve` 提出、使用者同意後修正。

```
現在 ❌                                          改後 ✓
指令文字裡先有 git、後有 commit 就擋              git 必須是該段指令的指令字，commit 是它的子指令
  → grep 的搜尋字串也被擋；subagent 把             → grep、echo、log --grep 不再誤擋
    deny 訊息誤判成 prompt injection
git -C <repo> commit 被「重用訊息」檢查放行        重用訊息的旗標只在 commit 之後找
  → improve／wrap-up 最常用的寫法從未被強制          → -C <repo> 是路徑，不再被當成 -C <commit>
建議的 Session 名稱取自 log 第一行                 最新的 customTitle 優先，log 第一行當備援
  → rename-session 之後仍是舊名
```

# Changes Made

- 判斷是否為 commit 的 regex 改為「段落開頭（或 `; & | (` 之後）→ 可選的環境變數指定 → `git` → 可選的 `-C／-c／--git-dir／--work-tree` → `commit`」。
- 「訊息重用」的檢查（`--no-edit`、`-C`、`--fixup` 等）只看 `commit` 之後的文字。
- Session 名稱來源順序對調：先掃 transcript 的最新 `customTitle`，沒有才讀 session log 第一行。

`bin/require-session-footer.py`

Result: 16 個案例全過（5 個應擋、11 個應放行，含 `git -C <repo> commit -C HEAD~1` 仍放行）；以本 session 的 transcript 實測，建議名稱為改名後的標題。`py_compile` 通過。

# Result

- 已知不涵蓋：`bash -c "git commit …"`、`xargs git commit` 這類 git 不在指令位置的寫法不會被擋。取捨是不再誤擋引號內的文字。
- 同一輪 `/improve` 另外在使用者的全域指示檔加了三條規則（不在本 repo）：gh 多帳號 404 的處理、描述 cwd 以外的 repo 前先確認 clone 新舊、「有某功能」的主張也要先確認有呼叫端。
