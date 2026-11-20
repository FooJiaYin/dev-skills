# TODO

## 未完成／未驗

- [ ] `code-review` 改版沒有實際跑過：路由（派／跳過表頭）、二元 verifier、standards 兩輪 SendMessage 都只讀過文字。在 `review-align` 分支對 main 跑一次確認（來源：plan Verification #2，2026-11-04）
- [ ] `/align start` 沒跑過；回歸測試：sparktoy 10/07 會議 → `_plan-2026-10-07-上架與圖片任務重整.md` → Notion task，應標出 I02「匯入預覽逐商品上傳圖片包」（來源：plan Verification #3，2026-11-04）
- [ ] wrap-up Full／Quick 新流程（quick-review → /align end → TODO.md）只改了文字，還沒在真的 wrap-up 跑過（來源：plan §5，2026-11-04）
- [ ] quick-review 的 gitleaks 路徑沒測（本機沒裝）；裝了之後用含 key 的 diff 測一次 `secret_scan: found`（來源：plan §2，2026-11-04）
- [ ] PR／CI tier（`pr-review` skill＋workflow yml）延後；引擎三選一：claude-code-action／codex-action／Anthropic hosted（來源：plan 延後，2026-11-04）
- [ ] `docs/site` 裡的 code-review 描述沒跟著改（來源：plan 延後，2026-11-04）
- [ ] 合併回 main 後跑 `/sync-org-forks`（來源：plan 延後，2026-11-04）
- [ ] `bin/notion-io.py` 的寫入路徑尚未實跑：`apply` 的 LINK `after` 插入 # Context、table_row 加註、續跑。用拋棄式測試頁跑一次，順便量總耗時對照原本的 23 分鐘（來源：notion-io plan Verification #4–5、#7，2026-11-11）
  - 已實跑（anchor 2026-11-19）：`apply` 建 2 張 task＋在會議頁與本機 .md 加註 3 處＋讀回、guest Assignee 保留、`Time: null` 保持空白；`upload-meeting` 上傳 4 份會議（含逐字稿 toggle）
- [ ] `fetch-task` pull 改走 `notion-io.py`（來源：notion-io plan 延後，2026-11-11）
- [ ] `notion-io.py sync-report` 尚未實跑 `.sync.json` 續傳（來源：sync-report 改用 script，2026-11-19）
  - 已實跑（anchor 2026-11-19）：5 張中文檔名截圖上傳、71 blocks append 到頁尾、Status／Time 寫入＋讀回、寫回 `last_synced`
- [ ] `notion-io.py upload-meeting` 不支援 `--dry-run`：`upload_meeting()` 沒有 dry 參數，加了旗標仍直接建頁（anchor 2026-11-19 實際誤建一頁）；拿它建 Tasks DB 的頁時 Assignee 變成 integration bot、Time 變成今天。改成支援 dry，或收到 `--dry-run` 時報錯（來源：/improve，2026-11-19；當時另一個 session 正在改此檔，所以未直接改）
- [ ] 做 proposal skill 時，參考對外提案頁的設計教訓：`/Users/unilife/Downloads/dropout/anchor/anchor-ai/docs/reports/2026-11-19-撰寫跨平台-plugin-方案簡述-omni-claude-code-codex-chatgpt-c1c063.md` 的「給之後 proposal skill 的設計教訓」一節（來源：/improve，2026-11-19）
- [ ] `sync-report` 之後的版本：重新同步只補差異、取代 task 上舊的 `# Unsolved Issues`、HTML artifact 嵌入、一份報告分給多張 task 時只貼對應段落（現在走 MCP 8b）（來源：sync-report 改用 script 延後，2026-11-19）
- [ ] dev-skills 自己沒有 Notion token 可找（Keychain 無 `notion-token`、往上無 `.env`）；在 dropout 以外的 repo 跑 `/sync-report` 會走 MCP 備案（來源：sync-report 改用 script，2026-11-19）
- [ ] Notion 託管圖片連結約 1 小時失效：腳本讀頁面時順便下載（來源：notion-io plan 延後，2026-11-11）
- [ ] `cleanup-processes` 的 `check.py` 有三個分支沒實跑過（寫的時候機器上沒有這些情況）：無畫面／帶自動化參數的 Chrome、colima 開著時「VM 上限 vs 容器實際用量」、idle 超過 1 小時的 session。下次遇到時對一次輸出（來源：cleanup-processes 交件報告，2026-11-19）
- [ ] `session-log.py` 的 `[agent]` hook 只手動加在這台的 `~/.claude/settings.json`（PreToolUse `Agent|Task|Workflow`、SubagentStop），repo 的安裝文件沒有記載；Claude 這邊的 session-log hook 設定整套都沒有文件（只有 Codex 的 `docs/hooks-codex-session-log.md`）。換一台機器不會生效也不會報錯（來源：使用者問「換台電腦可以跑嗎」，2026-11-19）
- [ ] 延後、等 `cleanup-processes` 用過再決定要不要做：(1) 工作紀錄加 `[proc]`，記下 session 用背景方式開了哪些 server／容器；(2) SessionEnd hook 關掉自己開的；(3) PreToolUse 上的門檻提醒（swap 用掉八成以上時提醒跑 `cleanup-processes`，十分鐘內只提醒一次）；(4) 主對話自己的慢指令記進工作紀錄（現在只有 agent 的 `slowest=`）（來源：本 session 討論，2026-11-19）

## 待客戶確認

- [ ] TODO.md 的格式（三節、每條格式、既有檔要不要統一）目前只是暫定，之後再討論（來源：使用者，2026-11-04）
- [ ] 個別安裝單一 skill（`gh skill install` 或只複製資料夾）時拿不到 repo 層的 `shared/review/commons.md`：要不要把 commons 複製進每個 review skill，或文件寫明只支援整包安裝？（來源：quick-review 自審 WR-02，2026-11-04）

## 需要人手操作

- [ ] Codex 雲端還沒設 environment（`codex cloud list` 回 `No tasks found`，沒有 `ENV_ID`）：到 chatgpt.com/codex 連要用的 repo（UniLife／dropout-tech 哪些待定）。設好前分流規則的「Codex 雲端」那條走不了，改走 Codex 本機（來源：本 session 分流規則，2026-11-20）
- [ ] 暫定：雲端任務成果由 agent 讀 `codex cloud diff` 抽查後才 `apply`，而不是讓 Codex 直接開 PR；要改成開 PR 再說（來源：本 session 分流規則，2026-11-20）
- [ ] 把 code-review 重設計的決定轉貼給 design session `ebd15042`（brief.md 只放設計素材、驗收流程進 plan、⑤ Flow 列用 `/align start`、quick-review 不用 impeccable）（來源：本 session 討論，2026-11-04）
- [ ] `brew install gitleaks`（來源：本 session 決定，2026-11-04）
- [ ] 這台機器上三台 11/12 開的孤兒 Python 伺服器（port 8765／8790／8791，pid 82222／61155／67898，工作目錄在 sontis-ai）還沒關：auto mode 擋了 `kill`。自己跑 `kill 82222 61155 67898`，或切 default mode 後請 agent 關。`cleanup-processes` 列為「要問」的也還沒決定：4 個等回覆的 session、20 個瀏覽器自動化背景程式、port 8831／18442 兩台伺服器（來源：cleanup-processes 第一次實跑，2026-11-19）
- [ ] sparktoy 的 Notion integration：建 integration、分享 Tasks DB 與會議記錄 DB、`security add-generic-password -U -a "$USER" -s notion-token-sparktoy -w`，並在 sparktoy `AGENTS.md` 的 `## Notion` 加 `Token: keychain notion-token-sparktoy`（來源：notion-io plan Verification #1，2026-11-11）
