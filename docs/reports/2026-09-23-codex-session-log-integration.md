---
session: codex-session-log-integration (01a0ca45-4de9-75e0-b72e-a49ba39904e7)
---

# Codex session log 與歷史搜尋

## Description

原本 `find-session`、`session-log.py` 的 `.log.md` 工作紀錄只處理 Claude。Codex 雖有保存對話，之前只能手動匯出逐字稿，無法用同一套工作紀錄搜尋或開啟歷史。這次在既有 [共用 session adapter](2026-09-23-unified-session-adapter.md) 上補上 Codex 路徑。

## Changes Made

- `bin/codex_history.py` 透過 Codex App Server 讀取指定 session 的完整分頁歷史，產生固定路徑的 `.log.md`。紀錄含使用者與助理文字、簡短工具活動、錯誤、壓縮標記、已完成的 `fileChange` 事件，並遮蔽符合既有規則的憑證字串。重新整理會更新既有紀錄；本機筆記另存並保留。
- `bin/session-adapter.py log` 新增按需更新、開啟與 `--watch` 持續更新；`bin/session-log.py` 的 show、note、writes、export、backfill 單一 session 操作可在 Codex 環境轉接。
- `find-session` 依當前 host 搜尋，或用 `--host` 指定；Codex 可搜尋目前專案／所有專案的對話與已完成檔案修改事件，`--open-id current` 能更新並開啟本次紀錄。
- 更新使用說明與技能指引，標明 Codex 紀錄的限制和 host 分流。

## Verification

- `python3 -m unittest discover -s tests -v`：17 項通過。含分頁與封存搜尋、檔案改名路徑、缺少 session ID 時拒絕猜測、重複更新、筆記保留、Codex／Claude 分流。
- 匯出回歸案例：用合成 `api_key=examplecredential123` 同時放在使用者、助理與本機筆記；`session-log.py export` 的 stdout 與檔案內容一致，均遮蔽憑證。原本的 `session-adapter.py export` 原始逐字稿行為未改。
- 實機：`session-adapter.py log` 讀取本次 Codex session 並產生紀錄；`find-session --host codex --topic dodo --scope cwd --limit 3` 找到 3 筆歷史；`--open-id current` 更新並在編輯器開啟；`--watch --interval 1` 第二輪更新後可用 Ctrl-C 結束；相容 CLI 的 writes／export 可執行。
- `quick_validate.py skills/find-session` 與 `git diff --check` 通過。

## Updates

- 審查發現 Codex 的 `session-log.py export` 原先轉接到未遮蔽的原始逐字稿；已改用遮蔽後輸出並加入 stdout／檔案回歸測試。獨立複審確認問題已解決。

## Result

Codex 現在可用同一個 `find-session` 流程讀取、搜尋及開啟工作紀錄。紀錄在呼叫時產生；`--watch` 僅在該指令執行期間輪詢。`[write]` 只代表已完成的 `fileChange`，無法可靠歸屬 shell／MCP 寫入，也沒有 Claude 的前後 blob 與分離共同編輯檔案的能力。Codex hook 自動更新是後續工作，未包含於此提交。
