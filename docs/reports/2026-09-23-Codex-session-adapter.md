# Codex session adapter

# Description

- dev-skills 從 Claude Code 搬到 Codex 後，`rename-session` 與 `/report transcript` 原本只能跳過：Claude 路徑直接操作 `~/.claude` JSONL／session log，而 Codex 沒有對應的 agent tool。實際檢查本機 `codex-cli 0.155.1` 後，確認 app-server protocol 已提供 `thread/read`、`thread/name/set` 與分頁 turns API，因此可以透過受支援的本機介面補齊功能，不需改 Codex SQLite 或直接解析 rollout JSONL。

# Changes Made

- 新增 `bin/codex-session.py`，提供三個命令：
  - `show`：使用 `thread/read` 顯示明確 thread 的名稱與 metadata。
  - `rename`：呼叫 `thread/name/set` 後重新 `thread/read`，儲存值不一致便失敗。
  - `export`：以 `thread/turns/list`、`sortDirection=asc`、`itemsView=full` 分頁讀取 turns；預設只輸出使用者／助理內容，`--full` 額外輸出命令、工具呼叫、檔案變更與截短後的結果。
- helper 只接受 `CODEX_THREAD_ID`、`CODEX_SESSION_ID` 或命令列 `--thread`。缺少明確 ID 時直接停止，不以 cwd、mtime 或「最新 session」猜測。
- `rename-session` skill 增加 Codex route；Claude Code 仍使用既有 `rename.sh`。
- `report` 的 transcript mode 增加 Codex route；Claude Code 既有 session-log／JSONL exporter 保持原樣。
- Full wrap-up 的 session hygiene 不再把 Codex rename 視為必須跳過；README 的 skill 摘要同步標示 Claude Code／Codex 都可改名。
- `references/agent-runtime.md` 與 README 的完整 Codex compatibility 區段目前由另一個 migration session 編輯，本次工作樹已補上正確內容，但 Quick commit 會排除這些 foreign hunks。

# Verification

## 靜態檢查

- `PYTHONPYCACHEPREFIX=/tmp/dev-skills-pycache python3 -m py_compile bin/codex-session.py`：通過。設定 cache 路徑是因 macOS system Python 預設 cache 位於 sandbox 外，第一次執行被拒絕，並非語法錯誤。
- `quick_validate.py` 分別檢查 `skills/rename-session`、`skills/report`、`skills/wrap-up`：三個皆回傳 `Skill is valid!`。
- `git diff --check`：通過，沒有 whitespace error。

## 真實 Codex app-server

- `python3 bin/codex-session.py show --json`：成功讀到本 session `01a0cab7-4292-7282-84db-a36db332fcf8`，名稱、cwd、來源、模型與 history mode 均正確。
- `python3 bin/codex-session.py export -o /tmp/codex-session-export-test.md`：成功輸出 14 turns、16,045 字元。檢查至少有一個 User 與 Assistant heading，且 readable mode 沒有 Tool heading。
- `python3 bin/codex-session.py export --full -o /tmp/codex-session-export-full-test.md`：成功輸出 14 turns、22,860 字元；檢查 full mode 包含 Tool heading 與實際工具活動。
- `python3 bin/codex-session.py rename '新增 Excel 匯入整批日期設定'`：以現有名稱做無副作用整合測試，寫入後回讀相同名稱，驗證 rename round trip。
- 移除 `CODEX_THREAD_ID`／`CODEX_SESSION_ID` 後加 `--thread 01a0…`：仍能成功讀取指定 session，確認歷史 thread 路徑。
- 同時移除環境 ID 且不傳 `--thread`：以 exit 1 停止並顯示 `No Codex thread ID`，沒有猜測其他 session。

# Result

- Codex 現在可透過 app-server 完成 session metadata 讀取、可靠改名與 Markdown transcript 匯出；sandbox 若阻擋 `~/.codex` state initialization，agent 可走正常 filesystem approval 後重試。
- 目前版本仍由 skill 自行判斷 Claude／Codex。下一步將依討論結果改成統一 `session-adapter.py` facade，讓 Claude 與 Codex 都成為 backend，skill 不再包含 host 分流細節。
