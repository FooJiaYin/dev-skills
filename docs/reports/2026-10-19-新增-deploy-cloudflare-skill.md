---
session: 2026-10-19-zeabur搬遷到cloudflare-pages (961ffc76-7c2e-4696-8bac-f5a07aec0329)
---

# 新增 deploy-cloudflare skill

# Description

- 來源：dropout 團隊把 5 個站從 Zeabur 搬到 Cloudflare Pages。過程中踩到的坑原本只記在對話裡，沒有可重用的地方；使用者在 `/improve` 要求寫成 `/deploy-cloudflare` skill。

# Changes Made

- `skills/deploy-cloudflare/SKILL.md`（新增）：憑證、建 Pages 專案、新舊對照、切換、搬 nameserver 五段，只寫流程骨架和實際踩過的坑：
  - 先加 Pages 自訂網域、後改 DNS，驗證會卡 `CNAME record not set`，522 約 2 分鐘。改成先改 DNS，再加網域，並立刻 PATCH 觸發重驗。
  - CF「Add a domain」從有代理的舊 zone 匯入時，會抓成 CF 自己的 IP（`104.21.*`／`172.67.*`）。改 nameserver 前必須修正。
  - 隨機 selector 的 DKIM 不會被匯入。
  - `<name>.pages.dev` 已被他人占用時，API 會回 `<name>-xxx`，驗證一律用 API 回傳的值。
  - wrangler OAuth token 約一小時過期；而且沒有 DNS 權限，需要另建 DNS token。
  - 直接上傳建立的 Pages 專案，之後不能改接 Git。
  - `_headers` 符合多條規則時會合併；`404.html` 會讓 SPA fallback 失效。
  - www 指向只支援 HTTP 的轉址服務，經過代理會 521。
- `skills/deploy-cloudflare/cfapi.sh`（新增）：用 wrangler OAuth token 呼叫 CF API，剩不到 10 分鐘就自動跑 `wrangler whoami` 刷新。

# Result

- 下次搬站或切 DNS 到 CF 時，可以直接用 `/deploy-cloudflare`。
- 實際的搬遷紀錄在 dodo 專案的 `docs/reports/2026-10-19-zeabur搬遷到cloudflare-pages.md`。
