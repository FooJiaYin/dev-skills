---
session: 2026-11-18-nextjs-upgrade (2d889843-1642-4aa1-8e31-d81d0fecc907)
---

# improve(sync-report)：Notion 把裸檔名自動變成 http 連結

# Description

- pimi 的 Next.js 升級報告同步到 Notion 時，`insert_content` 把正文裡沒包反引號的 `AGENTS.md`、`TODO.md` 自動轉成 `[AGENTS.md](http://AGENTS.md)` 這類假網址連結，要事後再用 `update_content` 拆掉。

# Changes Made

- `skills/sync-report/SKILL.md` 第 8 步：在 `update_content` 錨點說明後加一句——append 完 grep 抓回來的正文找 `](http://<name>.<ext>)`，用一次 `update_content` 拆掉。

# Result

- 之後的同步會在 append 後順手檢查並修掉這類假連結。
