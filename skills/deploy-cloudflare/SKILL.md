---
name: deploy-cloudflare
description: Deploy a site to Cloudflare Pages and cut its production domain over from another host (Zeabur, Vercel, a VM) with near-zero downtime and an instant rollback. Covers Git-connected Pages projects via API, env vars, old-vs-new comparison, DNS cutover, nameserver moves into CF. Use when the user says "/deploy-cloudflare", "搬到 Cloudflare", "上 Pages", "切 DNS 到 CF", or is migrating a site onto Cloudflare.
---

# deploy-cloudflare

## Credentials
- **Preferred: Account API Token per CF account** (Pages Edit + DNS Edit + Zone Read, no TTL or 90-day rotation), stored in macOS Keychain — read with `T=$(security find-generic-password -s cf-api-token-<account> -w)`, export as `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID` for wrangler. Never echo tokens; print length only. Have the user save it with `security add-generic-password -U -a "$USER" -s <name> -w` (interactive prompt, nothing in shell history).
- Fallback: **wrangler OAuth** (`npx wrangler login`): Pages/Workers only, **no DNS**, expires ~1h — `./cfapi.sh METHOD PATH [JSON]` refreshes via `wrangler whoami`.
- Domains can sit in different CF accounts — list `/zones` first and note each zone's account; account tokens don't span accounts.
- Mail keys: full-access key is admin-only (local Keychain); production gets a sending-only, single-domain key.

## Pages project
- Decide Git-connected vs direct upload **before** creating — a direct-upload project can never be switched to Git. Git needs the Cloudflare Pages GitHub App installed per CF account (error `8000011` = not installed).
- Create via API with `production_branch` = the migration branch until cutover; API-created projects don't build — POST `/deployments` once.
- **Use the `subdomain` the API returns** (`<name>-xxx.pages.dev` when the name is taken) — verifying `<name>.pages.dev` may hit someone else's site.
- Build-time env: copy the old host's values (ask the user to export them); don't reconstruct from the live bundle. Bun lockfile present → `SKIP_DEPENDENCY_INSTALL=1` + install in the build command.
- `_headers`: rules matching one path are concatenated — detach inherited values with `! Header`. `/foo.html` serves `/foo`; `/foo/index.html` 308s `/foo`→`/foo/`. A root `404.html` disables SPA fallback (dynamic routes then 404).

## Compare before cutover
curl old vs `*.pages.dev` for each route (with/without trailing slash, noindex, unknown, assets): status, Location, `<title>`, canonical, robots / X-Robots-Tag, Cache-Control. Old hosts may have ignored `_headers` — newly enforced CSP/XFO is a behavior change; diff header CSP against any meta CSP.

## Cutover (ask the user per site)
1. Back up the zone's records to JSON.
2. **Change DNS first**: A/CNAME → `CNAME <subdomain>.pages.dev`, proxied, comment with the rollback value.
3. Then POST `/pages/projects/<p>/domains`, then immediately PATCH `/domains/<d>` (empty body) to re-validate; repeat PATCH every ~30s until `active`. Adding the domain before the CNAME exists sticks at `pending: CNAME record not set` and serves 522 for minutes. Expect ~10–30s of 522 even when done right.
4. Re-run the comparison on the real domain; then merge the branch and set `production_branch` to `main` (+ trigger a main deploy).
- Rollback: restore the backed-up record (old A, proxied). Keep the old host running ~7 days.
- An existing www CNAME to an HTTP-only forwarder (e.g. Gandi `webredir`) is 521 behind the proxy — point www at Pages too.

## Moving a domain's nameservers into CF
"Add a domain" scans the old DNS. **If the old zone was proxied, apex/www/etc. import as Cloudflare anycast IPs (`104.21.*`, `172.67.*`, `2606:4700:*`)** — fix them to the real origin (`curl --resolve host:443:<ip>` to confirm) and match proxied/DNS-only to the old zone **before** the user changes nameservers. Random-selector DKIM (`<token>._domainkey`, e.g. SES) is never imported — ask the user to copy it from the old DNS panel. MX/SPF/SRV usually import fine; still diff against `dig`.
