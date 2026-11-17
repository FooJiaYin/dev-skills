---
session: 2026-11-18-商品圖片三票 (89078e74-4559-4d23-b730-ae4047dbfa59)
---

# improve：review 共用清單加「字串形狀變更」一條

## 摘要

| 現在 ❌ | 改後 ✓ |
|---|---|
| 共用清單沒有檢查「改了網址／檔名／識別字串的形狀，解析它的地方有沒有跟上」 | `shared/review/commons.md`「Added by /improve」加一行 |

# Description

sparktoy-erp 把刊登圖片公開網址從 `…/api/listing-images/<uuid>` 改成 `…/<uuid>.jpg`。露天發佈的程式用 `new URL(url).pathname.split("/").pop()` 取編號去找檔案，新網址會取到 `<uuid>.jpg`，每一筆新的露天發佈都會失敗。這次是因為派工 brief 明確要求 grep 才被抓到，quick-review 的清單裡沒有這一項。

# Changes Made

- `shared/review/commons.md`：加一行——diff 改了網址、檔名或識別字串的形狀時，所有解析或比對它的地方都要更新，已存的舊形狀值也要還能解析。

# 沒採用的建議

- 「交接單寫照 /wrap-up 走時要實際呼叫 /wrap-up」：使用者選擇不加。

# Unsolved Issues

- 這行還沒同步到 org fork（之後跑 `/sync-org-forks`）。
