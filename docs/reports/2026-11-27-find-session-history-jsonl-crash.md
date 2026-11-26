---
session: 2026-11-27-cloudflare-pages-cutover (ae3c659e-8c43-4b6a-ab9a-c571e10b5a03)
---

# find-session：掃到非 session 的 jsonl 時 Claude 搜尋報錯

# Description

- Reported by:
- `/find-session zeabur meetplus` 在 `--escalate` 擴到所有專案時，Claude 這邊報一個檔案讀不了，整次搜尋以結束碼 2（不完整）收場。使用者接著說「找太久」，再說「fix script」。

## Error Message

```
# incomplete: Claude history: 'int' object is not subscriptable
# host=all scope=all-bak matches=0 shown=0 unreadable=1
```

# Fix

## Cause

- `~/.claude/projects/.move-backup-08b4fd52-4070-4822-ac37-a9f1ab1c957b/history.jsonl` 不是 session 紀錄，但 `iter_session_files` 會把 projects 底下每個資料夾的 `*.jsonl` 都當成 session，檔名 `history` 就成了 session id（所以錯誤訊息是「Claude history」）。
- 這個檔每一行的 `timestamp` 是毫秒整數。`scan_session` 寫的是 `(d.get("timestamp") or "")[:19]`，對整數切片就丟 `TypeError`。
- 這個錯只讓那一個檔被標成讀不了，**不是搜尋回 0 筆的原因**：第一次 0 筆是因為關鍵字打成 `zeabut`，第二次是在跑完前被我停掉。

## Solutions

1. 在 `scan_session` 逐行解析後，跳過不是 dict 的行，`timestamp` 不是字串時當成空值。
   `skills/find-session/scripts/search.py`
   ```python
   if not isinstance(d, dict):
       continue
   # non-session jsonl (e.g. a history.jsonl backup) carries epoch-ms ints here
   ts = d.get("timestamp")
   ts = ts[:19] if isinstance(ts, str) else ""
   ```
   Result: Success。`python3 scripts/search.py --host claude --topic "zeabur meetplus" --scope all` 不再報錯，回 8 筆（5 個 session、3 個 subagent 紀錄）。

# Verification

- 修正前：`search.py --topic "zeabur meetplus" --escalate` → 上面的錯誤訊息，結束碼 2。
- 修正後：`search.py --host claude --topic "zeabur meetplus" --scope all` → `# no literal match …; matched all of: zeabur + meetplus`、`# scope=all  matches=8`，沒有錯誤行。
- 沒有驗證的：`--host all`（含 Codex）修正後沒有完整跑過一次；兩次都在跑完前被中斷，所以 Codex 那邊有沒有相關 session 不知道。

# Unsolved Issues

- 搜尋很慢：修正後 `--host claude --scope all` 實測 3 分 40 秒，CPU 只用 25 秒，其餘在讀大檔（最大的 jsonl 42 MB）；當時機器負載也很高，所以這個數字偏悲觀。直接 `grep -l` 兩個關鍵字再排序只要幾秒。可以改成先用 grep 篩出含關鍵字的檔再解析（deferred because: 使用者只要求修錯，速度沒有處理）。
- `iter_session_files` 仍會把 `.move-backup-*` 這類非專案資料夾的 jsonl 當成 session 掃；現在不會報錯，但會白掃（deferred because: 該資料夾裡也可能有真的 session，要不要排除沒有確認）。
- 這個修正沒有經過 `/quick-review`。
