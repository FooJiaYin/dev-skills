# 多 session 併行下的 skill 修正

## 摘要

```
踩到的                                     修在哪                          狀態
────────────────────────────────────────────────────────────────────────────────
點擊觸發導航 → drive 腳本整支崩潰           headless-shots (39b7363)        已推送
（寫入其實成功，每次都要再查 DB 才知道）

還沒給歸屬表就問「要不要一起 commit」        wrap-up/commit.md               本次
→ 用戶中斷：「到底是哪一個 session 未 commit」

/update-docs 在 commit 後跑，範圍是空的      update-docs/SKILL.md            本次
（該看的東西已經在 HEAD 裡）

文件寫著「0010/0011 尚未提交」                wrap-up/commit.md               本次
→ 我一 commit 就變成假的

中文檔名吐八進位，迴圈靜默比對失敗            git config --global             已生效
find -newermt "-15 minutes" 在 bfs 下失敗    ~/.claude/CLAUDE.md             已修
（而且被 2>/dev/null | wc -l 吞成 0）
```

# Description

一個 sparktoy-erp 的 session 全程與另一個 session 併行寫同一個 repo，暴露出 wrap-up / update-docs 在多寫入者情境下的幾個缺口，以及兩個環境層級的操作陷阱。

# Changes Made

## `skills/headless-shots/`（已於 39b7363 提交）

點下觸發 `revalidatePath` 的按鈕後，進行中的 `Runtime.evaluate` 收到 `Inspected target navigated or closed`，`p.rej()` 讓整支腳本崩潰 —— 但寫入已經成功。本次踩到兩次（後台還原預設、切換價格類型旗標），兩次都得另外查 DB 才知道有沒有生效。

- `drive-example.mjs` 訊息處理器改 resolve-with-error；`evalJs` 回 `{ __cdpError }`、`shot` 印 `SHOT SKIPPED`
- `SKILL.md` 既有的 fire-and-forget gotcha 補上判讀：該錯誤通常代表**動作已成功**，不可當失敗回報

## `skills/wrap-up/commit.md`

兩條加在 smart staging 開頭：

- **先給歸屬表再問 scope。** 工作樹含多個 session 的改動時，「要不要包含 X」在用戶不知道每批是誰的之前是無法回答的。實際發生：我直接問了，用戶中斷並反問「到底是哪一個 session 未 commit」。規則要求先印出「批次 → 檔案 → 誰的」，證據用每個檔 diff 的首行。
- **提交前拿即將提交的路徑去 grep 文件。** 寫著「尚未提交／untracked」的文件會在你提交的瞬間變成錯的，必須在同一個 commit 修掉。

同段附註中文檔名要用 `git -c core.quotepath=false`，否則 `while read f` 迴圈比對不到、靜默產生空結果。

## `skills/update-docs/SKILL.md`

範圍解析加 fallback：未提交 diff 為空、或不含本 session 的工作時，改用 `HEAD` 並在提案中明講。實際發生：wrap-up 提交完才跑 `/update-docs`，預設範圍只剩別人的殘留，我的改動一件都不在裡面。

## 環境層級

- `git config --global core.quotepath false` —— 中文檔名不再是 `\351\276\215...`
- `~/.claude/CLAUDE.md` 的併行偵測指令從 `-newermt "-15 minutes"` 改為 `-mmin -15`

# Result

兩個 skill 檔語法與內容已驗證。`core.quotepath` 設定後立即以 `git status` 確認中文檔名正常顯示；`-mmin -15` 以實際執行確認 exit 0 且行為正確。

# Unsolved Issues

- `find` 被 Claude Code shim 成 `bfs`，與 GNU find 的參數集不完全相同。這次只確認了 `-mmin` 可用，沒有系統性盤點還有哪些常用參數在 bfs 下會失敗。
- 本次的併行偵測規則寫在全域 CLAUDE.md，但沒有任何機制強制它在 wrap-up 之外被執行。
