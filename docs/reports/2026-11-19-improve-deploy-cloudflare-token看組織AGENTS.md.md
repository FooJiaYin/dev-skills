---
session: 2026-11-19 會議記錄（開發時程、AI 代理商與分鏡同頁） (76bf8600-0355-4f3b-bc12-9f655643cbf9)
---

# improve(deploy-cloudflare)：token 在哪看組織的 AGENTS.md

## 問題

sontis-ai 要在 Cloudflare 新增 sontis.ai，agent 說「沒有 Cloudflare token」。實際上 10/19 的 session 存過一把（`~/.config/cf-dns-token`）。文件寫的是「已搬進 Keychain」，但三處用了三個名字，搬家其實沒做。agent 只照文件查 Keychain 和 `.env`，就下了結論。

## 改動

- `skills/deploy-cloudflare/SKILL.md` Credentials 加一條：用哪把 token、放在哪裡，看組織 AGENTS.md 的 Cloudflare 段；沒讀之前不能說沒有 token。
- 使用者要求：token 細節只寫在組織層（`dropout/AGENTS.md`、`docs/cloudflare/demo-deploy.md`），skill 不寫具體路徑。token 已存進 Keychain `cf-api-token-dropout`，檔案留作備援。
- 另外在個人 `~/.claude/CLAUDE.md` 加一條：說某個 key／帳號不存在之前，先查組織 AGENTS.md 和過去的 session log（不在這個 repo）。
