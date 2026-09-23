# Codex session log hooks

`~/.codex/hooks.json` 在既有 handlers 之外，加入 `bin/codex-log-hook.py` 的四組命令 hook。程式使用事件的 `session_id` 經 App Server 刷新固定路徑的 `.log.md`，不讀取或解析原生 rollout JSONL。

| 事件 | 做法 |
|---|---|
| `SessionStart` | 啟動／恢復時刷新；resume／compact 回傳簡短 log 路徑，讓 agent 在需要時讀取。若 thread 尚未可讀，下一個事件會重試。 |
| `UserPromptSubmit` | 背景刷新，補齊上一輪已保存的訊息。 |
| `PostToolUse` | 對 Bash、apply_patch、Edit、Write 在背景刷新；先以同一 session 的非阻塞鎖避免並行重讀；五秒內已有新版時略過。 |
| `Stop` | 同步做最後一次刷新；只輸出合法的 `{}`，不阻斷回合。 |

handler 路徑：`/Users/unilife/agent-skills/dev-skills/bin/codex-log-hook.py`。設定保存在本機 `~/.codex/hooks.json`，原檔備份為 `~/.codex/hooks.json.backup.codex-session-log.2026-09-23`。更新時只附加新 groups，保留既有 Vibe Island handlers。程式不安裝常駐程序。

首次啟用必須在 Codex `/hooks` 審閱並信任**這四組新 hook**。`hooks/list` 顯示 `untrusted` 時，Codex 會略過執行；設定檔存在並不代表已自動記錄。信任後可送一則新訊息，待回合結束再執行 `find-session --open-id current` 檢查 log 有更新。

這是自動產生的**衍生工作紀錄**：只把 App Server 已保存的 `fileChange` 當寫入證據；shell／MCP 的檔案寫入、Claude 的 pre／post blob 與 co-edit 分離仍不在此版本。Stop 時若目前回合尚未保存，下一次 prompt／工具／開啟 log 時會補齊。憑證字串依 `session-log.py` 現有規則做模式遮蔽，分享前仍應檢查內容。
