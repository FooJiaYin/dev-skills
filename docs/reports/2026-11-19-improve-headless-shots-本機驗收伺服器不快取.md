---
session: 2026-11-19-demo-需求單與結構之間加-從素材庫選人物-商品-場景 (1c3bc112-4b97-4a18-b776-614f3c1cc6a3)
---

# improve：headless-shots 本機驗收伺服器不快取

# Description

- sontis-ai demo 素材步驟的驗收中，用 `python3 -m http.server` 開本機網址給使用者看；改了 demo.js 後使用者回「重新整理沒看到」——stdlib 伺服器不送快取標頭，瀏覽器沿用舊檔，而無頭 Chrome 每次是新 profile 所以驗證時看不出來。

# Changes Made

- `skills/headless-shots/scripts/serve-nocache.py`：新腳本，靜態檔伺服器、每個回應帶 `Cache-Control: no-store`（`python3 serve-nocache.py <dir> [port=8831]`）。
- `skills/headless-shots/SKILL.md` Gotchas 最後加一條：給使用者驗收的靜態頁用 `serve-nocache.py`，不要用 `python3 -m http.server`。
- 同一輪另加到使用者全域 `~/.claude/CLAUDE.md`（不在本 repo）：同一個動作在所有資料類型、所有入口用同一個元件，例外先問。

# Verification

- 在 sontis-ai 那個 session 用同樣內容的伺服器實跑：`curl -sI` 回 `Cache-Control: no-store`，新版 demo.js 有送出，使用者強制重新整理一次後之後改檔一般重新整理即可。

# Result

- 下次開本機驗收網址直接用 `serve-nocache.py`，不再有「重新整理沒看到」。
