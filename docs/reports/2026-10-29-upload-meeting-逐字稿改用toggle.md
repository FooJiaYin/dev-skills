# 2026-10-29 upload-meeting：逐字稿改用頁尾 toggle

| | 現在 ❌ | 改後 ✓ |
|---|---|---|
| 逐字稿位置 | `<meeting-notes>` 的 `<transcript>` 區塊 | 頁尾 `<toggle heading="h2">逐字稿` |
| §2 重複上傳 | 依 `<meeting-notes>` 判斷、retrofit／server-locked 分支 | 頁面沒有逐字稿 toggle 時可補上（`insert_content`），否則開啟或另建頁 |
| Hard constraints | write-once 規則、「必須用原生 block」 | 一條：不寫 `<meeting-notes>` 逐字稿區塊 |

**原因**：Notion 現行 markdown spec 註明 `<meeting-notes>` 的逐字稿區塊唯讀，不得加到新的會議記錄。小聰頭 10/29 會議上傳時照原步驟做不了，逐字稿沒有上傳。

**沒有改的**：§1 標題格式的 `<mention-date>`（會被存成純文字，正確寫法是 `<date start="…" />`）由使用者選擇不改 skill，只修正了 dropout 的 `AGENTS.md`。
