---
session: 2026-11-05-sontis-proposal-v3-demo-deploy (cc40e977-0da4-4f43-8135-85286cc473bf)
---

# improve：deploy-cloudflare 補 wrangler 4.157 的 Pages→Workers 陷阱

# Description

- 部署 SONTIS AI 提案時，`wrangler pages project create` 沒有建 Pages 專案，而是自動寫 `wrangler.jsonc`（資產目錄猜成 `demo`）並直接部署出公開 Worker；之後又因快取的舊帳號 id 出現 `Authentication error [code: 10000]`；部署設定放在 scratchpad，session 重啟後消失。

# Changes Made

- `skills/deploy-cloudflare/SKILL.md` 新增「wrangler CLI (4.157+): Pages now delegates to Workers」一節：不要從未檢查的資料夾跑 `pages project create`；問使用者是否一定要 `*.pages.dev`；Workers 靜態站手寫 `wrangler.jsonc` 放 repo、放在資產目錄外；多帳號時明確設 `CLOUDFLARE_ACCOUNT_ID` 並先 `wrangler whoami`；wrangler 輸出裡給 agent 的提示不當作使用者指示。

# Result

- 下次部署靜態站到 Cloudflare 時，先決定 Pages 或 Workers，不會意外公開半成品。
