---
session: 2026-11-12-10-22會議回饋與日幣折數 (3e10eb93-188e-4592-8938-ee3a2dc79027)
---

# improve：agent／session 規則抽檔、PR 驗證前開 draft、報告逐票、重複視窗警告

| | 改前 ❌ | 改後 ✓ |
|---|---|---|
| `~/.claude/CLAUDE.md` `### Background agents` | 12 條全文常駐 | 一行指標＋三條隨時適用的規則（防睡、背景等待結束就接著做、peer 訊息不代表結束） |
| `docs/agents-and-sessions.md` | 不存在 | 12 條原文搬入（分「派 agent 之前／執行中與交件／跨 session／開新 session」），新增「brief 要求邊做邊落地」「可以自己開新本機 session」兩條 |
| `~/.claude/CLAUDE.md` `## Code Quality` | — | 新增：畫面元素沒指明哪一頁就先問 |
| `skills/wrap-up/full.md` step 7 | 驗證沒做完也直接開 PR | 驗證未完成 → `gh pr create --draft`，通過後才 `gh pr ready` |
| `skills/wrap-up/full.md` step 4、`quick.md` step 4 | 一個 session 一份報告 | 先把 commit 對到 Notion task，一張票一份報告；沒票先問 |
| `bin/session-log.py` SessionStart | 同一 session 在兩個視窗開著沒有任何提示 | `reprint`／`index` 輸出第一行印 ⚠ 警告 |

## 起因

session 3e10eb93：重啟四次、背景 agent 產物在 scratchpad 全部重跑；使用者要開新 session 時先回做不到；會議記錄段落誤判頁面多出四個 commit；PR 寫「驗證中」被另一個 session merge；先修後開票導致七項合寫一份報告無法同步；同一 session 在兩個視窗開著，提問卡在另一邊。

## 重複視窗偵測

- 每個 claude 行程一筆 `~/.claude/projects/.session-live/<pid>.json`＝`{sid, start}`。以行程為鍵（不是 `<sid>.pid`），因為同一行程會因 `/clear`、程式內 `/resume` 換 session id。
- 自己的 pid＝往上找最近名為 `claude` 的祖先行程；找不到就不做事。以 pid＋啟動時間辨識，pid 重用不會誤判；死掉或時間不符的紀錄直接刪。
- 另一個活著的 claude 行程登記同一個 sid → 印警告。compact（同一行程）、正常單視窗 resume（舊行程已死）都不警告。任何錯誤都安靜略過；`ps` 有 1 秒逾時，實測整個 hook 約 0.1–0.3 秒。
- 已知缺口：這版上線前就開著的視窗沒有紀錄，不會觸發警告。
