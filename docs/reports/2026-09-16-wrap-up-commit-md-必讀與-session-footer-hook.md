# wrap-up：commit.md 改成必讀，Session footer 加 hook 擋門

## 摘要

```
現在 ❌                                          改後 ✓
────────────────────────────────────────────────────────────────────────────
Session: footer 規則                             Session: footer 規則
  只在 wrap-up/commit.md（SKILL → full/quick → commit.md 第三層）  三處：
  full.md step 7「Apply shared hygiene from ./commit.md」            ① ~/.claude/CLAUDE.md 全域規則（任何 git commit）
  → agent 當描述帶過，沒讀 → 5 筆 commit 沒 footer                  ② full.md / quick.md step 7「先 cat ./commit.md」
  非 wrap-up 的 commit（「commit」「continue commit」）→ 從未看到規則    ③ PreToolUse hook：git commit 沒 Session: → deny，附本 session 的 name/id

覆蓋率：2026-09-16 當天 11 筆只有 3 筆有 footer            當天 10 筆未推送的 commit 已用 commit-tree 重寫補上（tree 不變）
```

# Description

使用者問「為什麼最近的 commit 都沒有 session id」。追查 sparktoy-erp 的 commit 與各 session transcript：footer 規則只存在於 `wrap-up/commit.md`，而它是 SKILL.md → full.md → commit.md 的第三層引用。三種路徑都漏：(a) `/wrap-up full` 讀了 full.md 但沒讀 commit.md（session a7bc35a0，5 筆）；(b) 功能做完直接 checkpoint commit，在 /wrap-up 之前（同一 session，3 筆）；(c) 使用者說「commit」／「continue commit」的 session 根本沒載入 wrap-up（06630af7、792fdace，3 筆）。plugin cache 與 source 的 commit.md 一致，不是快取過期。

# Changes Made

| 檔案 | 改動 |
|---|---|
| `skills/wrap-up/full.md` step 7 | 「Apply shared commit hygiene from ./commit.md」→ 明確「Read `./commit.md` now (`cat` it) — do not commit from memory」，並點名 footer 為必填 |
| `skills/wrap-up/quick.md` Step 7 | 同上 |
| `~/.claude/CLAUDE.md`（本機，非本 repo） | Git history safety 新增：所有 git commit 都附 `Session: <name> (<id>)`，含 id／name 取法 |
| `~/.claude/hooks/require-session-footer.py` ＋ `settings.json`（本機） | PreToolUse(Bash) hook：指令含 `git commit` 且訊息沒 `Session:` → deny，回覆裡帶本 session 的 name（jsonl 最新 customTitle）與 id；`--amend --no-edit`／`-C`／`--fixup` 放行；`-F <file>` 會讀檔內容檢查 |
| sparktoy-erp `feat/meeting-0902-c1-c7` | 10 筆未推送 commit 以 `git commit-tree` 逐筆重建（同 tree、同 author/committer 日期），只插入 footer；`update-ref` 帶舊 HEAD 守衛，工作樹（16 個 dirty 檔）完全未動 |

# Result

- hook 三案例實測：缺 footer → deny 並附 `Session: <name> (<id>)`；有 footer → 放行；非 commit 指令 → 放行。
- 重寫後 `git diff b1c952c HEAD` 為空（內容零變動），`git log ce41671..HEAD` 10 筆皆帶 footer。
- 兩個沒 customTitle 的 session（06630af7、792fdace）依規則以主題當 name。

# Unsolved Issues

- hook 只看 Bash 指令文字；`git commit` 走互動編輯器（不帶 -m／-F）時沒有訊息可查，會被放行。agent 不會走這條路，可接受。
- 已推送的更早 commit 不回頭改。
