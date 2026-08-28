# headless-shots skill：Playwright MCP 被鎖時的 headless Chrome + CDP 截圖／表單驅動

# Description

- sparktoy-erp UI 重構 session 中，Playwright MCP 瀏覽器持續回 `Browser is already in use`（另一個 session 佔住 profile）。為了驗證登入後的頁面與售價寫入路徑，改用系統的 Google Chrome `--headless=new` + `--remote-debugging-port`，以 Node 24 內建 `WebSocket` 走 CDP。`/improve` 後收成 skill。

# Changes Made

- 新增 `skills/headless-shots/SKILL.md`：何時用（截圖／驗證渲染／驅動表單／MCP 鎖住）、cookie 自行 mint（不借真人 cookie）、寫入測試一定要回 DB 用 SQL 驗證、port／profile 隔離、`captureBeyondViewport` 高度上限。
- `skills/headless-shots/scripts/shoot.mjs`：帶 cookie 逐頁全頁 PNG。
- `skills/headless-shots/scripts/drive-example.mjs`：React 安全的 `__setInput`（native setter + `input` event）／`__setSelect`／`__byLabel`／`__btn` helper，示範「套用建議值→儲存」與「建檔帶條碼」兩個情境。
- `references/erp-ui-directions/`：sparktoy-erp 四個 UI 風格方向的 `.dc.html` artboard + README（token 表），供之後其他 ERP 參考。

Result: 在 sparktoy-erp 上實跑成功（登入後截圖 4 頁、兩個寫入情境皆以 SQL 驗證）。

# Result

- 記憶指標：`headless-shots-skill`（sparktoy 專案記憶）。
- 未做：把 drive 腳本一般化成「步驟 JSON」驅動器；目前是複製範例再改情境。
