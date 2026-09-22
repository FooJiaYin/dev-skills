---
session: unified-session-adapter (01a0cab7-4292-7282-84db-a36db332fcf8)
---

# Unified session adapter

# Description

前一階段以 `bin/codex-session.py` 補上 Codex 的 session 改名與 transcript 匯出，但 skill 仍需自行判斷 Claude Code／Codex 並維護兩套呼叫方式。本次將 host 差異收進同一個 facade，使 `rename-session` 與 `report transcript` 只需要呼叫一組 `show`、`rename`、`export` 命令；Claude Code 與 Codex 各自保留原本受支援且已驗證的底層實作。

# Changes Made

- 新增 `bin/session-adapter.py` 作為共用 CLI：
  - `show` 顯示 title、session ID 與 host，`--json` 可輸出 metadata。
  - `rename` 寫入 title 後重新讀取，實際值不一致即失敗。
  - `export` 預設輸出 readable Markdown；`--full` 加入工具活動；Claude 額外支援 `--since`。
- host 解析優先使用明確的 `--host`，否則依 `CODEX_THREAD_ID`／`CODEX_SESSION_ID` 或 `CLAUDE_CODE_SESSION_ID`／`CLAUDE_SESSION_ID` 判斷。session identity 只接受 `--session` 或該 host 的環境變數，缺少時停止，不猜測最新紀錄。
- Codex backend 沿用 app-server protocol：
  - `thread/read` 取得 metadata。
  - `thread/name/set` 寫入名稱後再次 `thread/read` 驗證。
  - `thread/turns/list` 以 ascending/full view 分頁輸出 transcript。
  - 不直接修改 SQLite，也不解析 rollout JSONL。
- Claude backend 委派既有工具：
  - title 讀取與 full／舊 session 匯出使用 `skills/report/export-transcript.py`。
  - rename 使用 `skills/rename-session/rename.sh`，並移除子程序環境中的 Codex ID，避免跨 host 誤判。
  - readable export 在有 session log 時優先使用 `bin/session-log.py` 的已過濾、已遮蔽輸出；只有明確回報「沒有 session log」才降級到 JSONL exporter，其他錯誤直接向上回報。
- `--thread` 保留為 `--session` 的 alias；`bin/codex-session.py` 改為八行相容 shim，因此前一版 Codex 指令仍可運作。
- `rename-session` 與 `report` skill 改呼叫共用 adapter，移除 skill 內部的 Claude／Codex 分流步驟。

# Verification

## 靜態與 skill 格式

- `PYTHONPYCACHEPREFIX=/tmp/dev-skills-pycache python3 -m py_compile bin/session-adapter.py bin/codex-session.py skills/report/export-transcript.py bin/session-log.py`：通過。`PYTHONPYCACHEPREFIX` 避免 macOS system Python 嘗試寫入 sandbox 外的使用者 cache。
- `quick_validate.py skills/rename-session`、`quick_validate.py skills/report`、`quick_validate.py skills/wrap-up`：全部回傳 `Skill is valid!`。
- `git diff --check`：通過，沒有 whitespace error。
- CLI help：主命令及 `export` 子命令均能列出 `show / rename / export`、`--host`、`--session`、`--thread`、`--full`、`--since` 等參數。

## Codex backend 真實整合

- `python3 bin/session-adapter.py show --json`：透過本機 app-server 成功讀取目前 thread `01a0cab7-4292-7282-84db-a36db332fcf8`，回傳名稱 `Codex session adapter`、cwd、模型、來源與 `host: codex`。
- `python3 bin/session-adapter.py export -o /tmp/session-adapter-codex-readable.md`：成功讀取 16 turns；adapter 報告 20,791 個字元。內容包含 User／Assistant headings，未加入 Tool headings。
- `python3 bin/session-adapter.py export --full -o /tmp/session-adapter-codex-full.md`：成功讀取相同 16 turns；adapter 報告 29,249 個字元，內容包含實際工具活動。
- `python3 bin/session-adapter.py rename 'Codex session adapter'`：以現有名稱做無副作用 round trip，`thread/name/set` 後重新讀取相同名稱。
- `python3 bin/codex-session.py show --thread "$CODEX_THREAD_ID"`：舊入口與 `--thread` alias 均成功，輸出相同 session ID 與 `[codex]`。

## Claude backend 隔離 fixture

- 在 `/tmp/session-adapter-home` 建立兩輪 user／assistant JSONL fixture。`show --host claude --session <id> --json` 在改名前回傳 `titleSource: none`。
- `rename 'Fixture adapter session' --host claude --session <id>`：`rename.sh` 寫入 custom-title，adapter 重新讀取後確認 `titleSource: custom-title` 且名稱完全相同。
- 無 `.log.md` 時執行 readable export：session-log 明確回報不存在後，成功降級到 JSONL exporter；輸出包含 `Verify the shared adapter.` 與 `The Claude JSONL fallback works.`。
- 有 `.log.md` 時執行 readable export：優先走 session-log；fixture 中的 `api_key=abcdefghijklmnop` 輸出為 `api_key=[REDACTED]`。
- `--full`：成功委派 `export-transcript.py`，輸出完整 fixture 對話。
- 移除所有 Claude／Codex session ID 且不傳 `--host`／`--session`：exit 1，訊息要求明確 host/session，不猜測其他 session。

## 簡單 code review

- 檢查 host 誤判、歷史 session 指定、舊 CLI 相容、rename read-back、session-log 降級與其他 session 檔案隔離。
- 發現 session-log 初版會在任何錯誤時靜默降級到 JSONL，可能掩蓋輸出路徑或執行錯誤。已限制為只有 `no session log for ...` 才 fallback；修改後重新驗證「有 log」與「無 log」兩條路徑皆通過。
- 沒有剩餘的 Critical／Warning finding。

# Result

- Claude Code 與 Codex 現在都能透過 `python3 bin/session-adapter.py <show|rename|export>` 操作 session，skill 不再需要知道各 host 的儲存方式。
- Codex 維持受支援的 app-server 邊界；Claude Code 繼續使用成熟的 session log、JSONL exporter 與 rename script。
- 本次 Quick wrap-up 依使用者指示不 push；完整品質流程中的 `/verify`、多 agent `/code-review`、deploy 與 `/improve` 亦按 Quick 模式跳過。本次實作前已做上述針對性的整合驗證與簡單人工 review。

# Updates

## 2026-09-23：Codex 結構化提問工具映射

- 修正 compatibility 說明的模糊處：shared skill 中的 Claude Code `AskUserQuestion` 在 Codex 應對應 `request_user_input`，前提是目前 host/client 有 expose 該工具；不應因工具名稱不同而直接退回純文字問題。
- README 已明確記錄此映射。偏好或澄清問題使用結構化提問；shell sandbox permission 仍走 host escalation approval；只有工具未提供時才使用簡短 chat 問句。
- `git show -- README.md` 確認本次 commit 只新增五行映射說明；`git diff --cached --name-only` 在提交後為空，沒有納入 Codex thread `01a0c89a-35ee-7611-9189-a25de549876c` 的 README migration 區段。
- 此更新只有文件映射，未執行應用程式測試；Quick 模式跳過正式 `/verify` 與多 agent `/code-review`。

# Suggested Doc Updates

- `README.md` 已新增可獨立提交的共用入口說明，記錄 `bin/session-adapter.py` 的 `show / rename / export` 與 `bin/codex-session.py` 相容 shim。
- README 的完整 Codex compatibility table 與 `references/agent-runtime.md` 目前屬於 Codex thread `01a0c89a-35ee-7611-9189-a25de549876c`（`Investigate Claude Code settings`）尚未提交的 migration。該 session 後續提交時，應把表格與 runtime guide 的 Codex-only helper 敘述更新為共用 facade，並在 `AskUserQuestion` mapping 直接寫出 `request_user_input`；本次不夾帶它的其餘 hunks。
