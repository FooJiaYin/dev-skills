# 2026-11-19 improve：`/sync-report` 改用 script 寫 Notion

## 摘要

```
現在 ❌                                   改後 ✓
agent 用 Notion MCP 逐字重打報告內文      agent 只做判斷（貼哪張 task、Status、Github Link、問使用者）
  ├ 9 千多字當工具參數送出（送了兩次）       └► notion-io.py sync-report 讀檔直接送，內文不經過模型
  ├ 表格裡的圖片 → 整份被 400 拒絕          ├ 圖片一張一行，script 上傳成獨立圖片區塊；在表格／清單裡就 exit 2
  ├ 屬性併進 update_content 被靜默忽略      ├ 屬性另外 PATCH、回讀，不一致重送一次，仍不對就 exit 1
  └ 上傳 ≤3 個、各自 curl、憑證印在對話     └ 上傳在 script 內，token 不進對話
沒有 token → —                            exit 3 → 走 MCP 備案（skill 保留，加上兩條修正）
```

| 改在哪裡 | 內容 |
|---|---|
| `bin/notion-io.py` | 新子指令 `sync-report`；`md_blocks` 加 `image=` 參數（單獨一行的 `![alt](src)` → 圖片區塊，不傳就照舊）；`upload_file`（File Upload API 單段）；`h1_sections`／`norm`／`page_sections`（比對 task 上已有的段落）；`Stop`（exit 2／4）；exit code 4 |
| `skills/sync-report/SKILL.md` | 步驟 8 改成先跑 script；原本的 MCP 做法改成 8b「備案（exit 3）」，屬性改成另外 `update_properties` 並 SQL 回讀；圖片不能放在表格或清單；步驟 5「新建」與步驟 9 對應調整 |
| `skills/report/SKILL.md` | 截圖一張一行 `![說明](路徑)`，不放在表格或清單 |
| `README.md` | 「Notion writes via API」加上 `/sync-report` |
| `TODO.md` | 原本的「sync-report 改走 notion-io.py」改成只剩 fetch-task；新增實際寫入沒測、延後項目、dev-skills 沒 token |

## script 的流程

```
sync-report <report.md> [--page] [--status] [--github] [--time A [B]] [--force] [--dry-run [--offline]] [--blocks-out F]
 1 讀報告、去掉 frontmatter 和整行的 <!-- … --> 註解
 2 抓 task 內文，依 H1 分段；報告開頭的 H1 段落如果 task 上有同名段落：
     內容一樣（只比字，去掉標記、網址、mention、圖片）→ 不貼
     內容不一樣 → exit 4（請 agent 問使用者；--force 從這段開始貼）
 3 轉成區塊；有圖片在表格或清單裡、或圖檔不存在 → exit 2
 4 先驗證屬性（Status 選項、Github Link 欄位；已有值就不覆寫）——寫入前全部驗完
 5 上傳圖片 → 貼到頁尾 → 寫屬性＋回讀 → 寫回 notion.last_synced
   每一步記在 <report>.sync.json；失敗後重跑同一個指令會從斷點接著做，全部成功後刪掉
```

## 設計決定

- **「已經同步過」的判斷靠 task 上的標題，不靠 `last_synced`。** `/fetch-task` 寫的 `last_synced` 會跟著 task 檔帶進報告，所以有這個欄位不代表報告貼過了。
- **表格裡的圖片不做轉換，直接報錯**（使用者決定：在 `/report` 規定不要這樣寫，程式不額外處理）。報錯是為了不讓 `![](…)` 變成文字貼上去。
- **`--force` 的意思是「從第一個不一樣的段落開始貼」；`--skip "<H1>"` 是把開頭某段拿掉不貼。** 例如 task 上的 `# Context` 比本機新，就用 `--skip`。第一版不做差異同步。
- **報告後面的段落如果 task 上已經有同名的（通常是 `# Unsolved Issues`），script 照樣貼，但會在摘要提醒**，由 agent 照 8b 的規則處理舊的那段，不留兩份。
- **一份報告分給多張 task 的情況先走 8b（MCP）**，因為 script 會貼整份報告。已記進 TODO。
- **續傳時碰到「上次貼到一半」不會自動重送內文**，要使用者看過 task 後用 `--force` 或手動把狀態改成 done。
- Cloudflare 擋 HTML 標籤、`update_content` 錨點、裸檔名自動變連結，這三條都是在 MCP 上遇到的，留在 8b 備案，script 不處理。API 路徑上會不會遇到同樣的問題還沒驗證。

## 驗證

| 檢查 | 結果 |
|---|---|
| 原始樣本報告（`sontis-ai/docs/reports/2026-11-19-demo-需求單加影片比例-a189e1.md`，圖片在表格裡）離線 dry-run | exit 2，列出 6 張在表格裡的圖 ✓ |
| scratchpad 複本（改成一張一行）離線 dry-run | 57 個區塊、6 張圖片、沒有殘留 `![` ✓ |
| 複本對真的 task 唯讀 dry-run（task 已經有 MCP 貼過的整份報告） | `# Context`、`# Changes Made` 判定為一樣；`# Verification` 因為複本改了截圖排版而不同 → exit 4，訊息寫「看起來已同步」✓ |
| 同上加 `--force --status "Completed 🙌" --time … --github …` | 從 `# Verification` 開始 40 個區塊；Status、Time 要寫；Github Link 已有值 → 保留 ✓ |
| `--status Done`（不存在的選項） | exit 2，列出可用選項 ✓ |
| `--skip Context --force` | 跳過 Context；摘要列出 task 上已有的 `# Verification`、`# Updates`、`# Result`、`# Unsolved Issues`，提醒會變成兩份 ✓ |
| 這份報告本身（反引號裡寫了 `![alt](src)`）離線 dry-run | 不會被誤判成表格裡的圖 ✓ |
| 轉換有沒有掉字：8 份報告比對「Markdown 的純文字」和「轉出區塊的純文字」 | 8/8 完全相同 ✓ |
| `upload-meeting` 的行為 | `md_blocks` 沒傳 `image=` 就跟原本一樣（程式碼確認，沒有實跑） |
| `POST /file_uploads` 的欄位 | 查 API reference：單段模式可以帶 `filename`、`content_type` ✓ |

第一次對真 task 跑時抓到一個 bug：task 上 `<b>2. 做影片的流程</b>` 被存成編號清單（文字裡沒有「2.」），本機那邊卻先去掉清單符號才去掉標籤，所以比對失敗。改成先去標籤之後就對了。

**沒測的**：實際寫入（上傳、貼內文、寫屬性、續傳、寫回 frontmatter）。使用者選了只跑 dry-run，這件事已記進 `TODO.md`。

## 交接時說的兩條小修正

1. 屬性不能跟 `update_content` 放在同一個呼叫 → script 本來就分開寫；MCP 備案 8b 也改成另外呼叫並回讀。
2. 截圖一張一行，不放在表格或清單 → 寫進 `report` skill；script 碰到就報錯；8b 也加上這條。

## 來源

- 交接檔：SONTIS session `2026-11-19-demo-需求單加影片比例`（`sontis-ai-0b`）。使用者原話：「sync report 不是用script嗎」「開新session處理」。
- 本 session 跟使用者確認了：照第一版範圍做；表格裡的圖片由 `/report` 規定、script 不處理；只 commit 自己的部分；只跑 dry-run。
