# improve：find-session 補「jsonl 使用者訊息在三處」

## 摘要

| | 現在 ❌ | 改後 ✓ |
|---|---|---|
| 自己抽 Claude jsonl | 只讀 `type=user/assistant`，漏掉對話中途插話與排隊訊息 | Pitfalls 一條：使用者訊息在 `user`、`attachment.queued_command`、`queue-operation enqueue` 三處；app 對話框另有紀錄且 `user` 列可能是 agent 測試；時間是 UTC |

## 來源

sontis-ai session 18df74af（2026-11-26，懶懶 EP1 影片製作流程報告）：自寫的抽取腳本只讀 user/assistant，交給 6 個 agent 寫報告；G3 交件才發現中途插話不見，之後補抽 97 則 queued_command，再比對 enqueue 又找到使用者 7 則＋跨 session／subagent 81 則，分鏡編輯器 chat-log.jsonl 最後才找到（其中一則 user 是 agent 用瀏覽器測試填的）。raw 時間是 UTC，agent 換算不一，事後逐份要求改成台灣時間。

## 改動

- `skills/find-session/SKILL.md` § Pitfalls 加一條（1 行）。

## 沒採用

- agents-and-sessions.md 加「brief 禁止刪非自建檔、禁止 import 會送單的腳本」「依來源分組時一段只給一個 agent、回報實讀範圍」：使用者選 Skip。
- 「記錄流程要含 agent 觀察、建議、結果」存 memory：使用者選 Skip。
