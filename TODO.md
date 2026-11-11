# TODO

## 未完成／未驗

- [ ] `code-review` 改版沒有實際跑過：路由（派／跳過表頭）、二元 verifier、standards 兩輪 SendMessage 都只讀過文字。在 `review-align` 分支對 main 跑一次確認（來源：plan Verification #2，2026-11-04）
- [ ] `/align start` 沒跑過；回歸測試：sparktoy 10/07 會議 → `_plan-2026-10-07-上架與圖片任務重整.md` → Notion task，應標出 I02「匯入預覽逐商品上傳圖片包」（來源：plan Verification #3，2026-11-04）
- [ ] wrap-up Full／Quick 新流程（quick-review → /align end → TODO.md）只改了文字，還沒在真的 wrap-up 跑過（來源：plan §5，2026-11-04）
- [ ] quick-review 的 gitleaks 路徑沒測（本機沒裝）；裝了之後用含 key 的 diff 測一次 `secret_scan: found`（來源：plan §2，2026-11-04）
- [ ] PR／CI tier（`pr-review` skill＋workflow yml）延後；引擎三選一：claude-code-action／codex-action／Anthropic hosted（來源：plan 延後，2026-11-04）
- [ ] `docs/site` 裡的 code-review 描述沒跟著改（來源：plan 延後，2026-11-04）
- [ ] 合併回 main 後跑 `/sync-org-forks`（來源：plan 延後，2026-11-04）
- [ ] `bin/notion-io.py` 的寫入路徑還沒實跑：`apply`（建立、`after` 插入 # Context、table_row 加註、讀回比對）、`upload-meeting`、guest Assignee 不被改成 OAuth 帳號、`Time: null` 保持空白，都只驗了離線解析與唯讀 schema。用拋棄式測試頁跑一次（來源：notion-io plan Verification #4–5，2026-11-11）
- [ ] `sync-report` append、`fetch-task` pull 改走 `notion-io.py`（來源：notion-io plan 延後，2026-11-11）
- [ ] Notion 託管圖片連結約 1 小時失效：腳本讀頁面時順便下載（來源：notion-io plan 延後，2026-11-11）

## 待客戶確認

- [ ] TODO.md 的格式（三節、每條格式、既有檔要不要統一）目前只是暫定，之後再討論（來源：使用者，2026-11-04）
- [ ] 個別安裝單一 skill（`gh skill install` 或只複製資料夾）時拿不到 repo 層的 `shared/review/commons.md`：要不要把 commons 複製進每個 review skill，或文件寫明只支援整包安裝？（來源：quick-review 自審 WR-02，2026-11-04）

## 需要人手操作

- [ ] 把 code-review 重設計的決定轉貼給 design session `ebd15042`（brief.md 只放設計素材、驗收流程進 plan、⑤ Flow 列用 `/align start`、quick-review 不用 impeccable）（來源：本 session 討論，2026-11-04）
- [ ] `brew install gitleaks`（來源：本 session 決定，2026-11-04）
- [ ] sparktoy 的 Notion integration：建 integration、分享 Tasks DB 與會議記錄 DB、`security add-generic-password -U -a "$USER" -s notion-token-sparktoy -w`，並在 sparktoy `AGENTS.md` 的 `## Notion` 加 `Token: keychain notion-token-sparktoy`（來源：notion-io plan Verification #1，2026-11-11）
