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

2. （`/improve` 追加）搜尋前先整檔篩一次關鍵字，不含的檔直接跳過，不逐行解析。
   `skills/find-session/scripts/search.py`：`topic_needles()`、`may_contain_topic()`，在 `scan_session` 開頭呼叫。
   - 比對是在解碼後的文字上做、篩選是在原始位元組上做，所以只有兩邊寫法一定相同的關鍵字才篩：含 `"`、`\`、`/`、控制字元，或含有大小寫之分的非 ASCII 字母（如 `Ü`）時不篩，照舊逐檔解析。
   - 非 ASCII 文字在檔案裡可能是原字、也可能是 `\uXXXX`，兩種都當成篩選字串。
   Result: Success。同一台機器、負載 2 左右時：

   | 查詢（`--host claude --scope all`） | 改之前 | 改之後 | 輸出 |
   |---|---|---|---|
   | `zeabur meetplus` | 16.35 秒 | 9.37 秒 | 逐位元組相同 |
   | `折價券通知` | 7.65 秒 | 2.98 秒 | 逐位元組相同 |

# Verification

- **先篩再解析的結果一致性**：`Cloudflare`、`notify-mail.js`、`a/b`（不篩的情況）、`pages.dev`、`米特`（10 筆命中）、`切換模式`（2 筆命中）六個查詢，改之前與改之後的完整輸出相同。
- `python3 -m unittest discover -s tests -p 'test_session_search_all.py'` → 9 項通過。
- `topic_needles` 對樣本的判斷：`Zeabur` → `zeabur`；`折價券` → 原字與 `折價券` 兩種；`a/b`、`say "hi"`、`Ünï`、含 tab 的字串 → 不篩。
- 修正前：`search.py --topic "zeabur meetplus" --escalate` → 上面的錯誤訊息，結束碼 2。
- 修正後：`search.py --host claude --topic "zeabur meetplus" --scope all` → `# no literal match …; matched all of: zeabur + meetplus`、`# scope=all  matches=8`，沒有錯誤行。
- 沒有驗證的：`--host all`（含 Codex）修正後沒有完整跑過一次；兩次都在跑完前被中斷，所以 Codex 那邊有沒有相關 session 不知道。

# Unsolved Issues

- 第一次量到的 3 分 40 秒是機器被其他工作佔滿（負載 45 以上）時的數字；負載 2 左右時原本是 16 秒。先篩之後剩下的 9 秒，花在含關鍵字的大檔仍要逐行解析（最大的 jsonl 42 MB），以及多字查詢會先試整句、再試每個字。沒有再往下優化。
- Codex 那一側（`--host all`）的速度沒有量，也沒有改。
- `iter_session_files` 仍會把 `.move-backup-*` 這類非專案資料夾的 jsonl 當成 session 掃；現在不會報錯，但會白掃（deferred because: 該資料夾裡也可能有真的 session，要不要排除沒有確認）。
- 這個修正沒有經過 `/quick-review`。
