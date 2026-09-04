---
name: headless-shots
description: Screenshot or drive a locally running web app through headless Google Chrome + CDP with a pre-set login cookie — the fallback when the Playwright MCP browser is locked ("Browser is already in use") or when you need authenticated pages / form submits verified against the DB. Use when asked to "截圖", "screenshot the app", "verify the page renders", "drive the form", or when browser MCP tools fail with a lock error.
---

# headless-shots

Headless Chrome (`/Applications/Google Chrome.app`) + CDP over Node 24's built-in `WebSocket`. No deps.

## Screenshots
```bash
node scripts/shoot.mjs <cookieValue> <outDir> /path1 /path2 ...
```
Edit the cookie name (`sparktoy_session`) and base URL (`localhost:3000`) at the top of the script if the app differs. Full-page PNG per path; `Read` the PNGs and fix what you see.

Mint a session cookie the same way the app does (e.g. jose HS256 with `SESSION_SECRET` from `.env.local`; find the payload shape in the app's `session.ts`) — never reuse a real user's browser cookie.

## Driving forms (write-path tests)
`scripts/drive-example.mjs` shows the pattern: inject helpers (`__setInput` uses the native value setter + `input` event so React controlled inputs register; `__setSelect` dispatches `change`; `__byLabel` finds a control by its label text; `__btn` by button text), click, wait, read `location.pathname` + error text, screenshot. Copy it, replace the scenario, then **verify the result in the DB with SQL** — a 200 render proves nothing about writes.

## Gotchas
- **A `window.confirm` / `alert` freezes the whole CDP connection, silently.** The page stops, *no request reaches the server*, and every later `Runtime.evaluate` hangs with no error — it looks like "the button did nothing". Always `Page.enable` and auto-accept `Page.javascriptDialogOpening` (see `drive-example.mjs`). Forms with unsaved-changes / inheritance / delete confirmations hit this constantly.
- **A click that triggers navigation must be fire-and-forget.** `Runtime.evaluate` never returns once the page starts navigating — send the click with a bare `ws.send(...)` and don't await it, then verify the result in the DB rather than reading the DOM afterwards.
- **`Page.captureScreenshot` can wedge the connection, not just itself.** Once it stalls, every subsequent CDP call hangs too (a `Promise.race` timeout on the screenshot does *not* free it). For write-path verification prefer DOM assertions + SQL over PNGs; take shots only at the end, or skip them.
- Give the script a hard self-timeout (`setTimeout(() => { chrome.kill(); process.exit(3) }, 90_000)`) so a wedged connection fails loudly instead of hanging the tool call.
- Dev-mode server actions compile on first call — allow 20s+ after submitting before killing Chrome, or the action is aborted mid-flight and nothing is written.
- Use a distinct `--remote-debugging-port` and `--user-data-dir` per script so runs don't collide.
- `Emulation.setDeviceMetricsOverride` + `captureBeyondViewport` for full-page shots; cap height (~6000) or Chrome stalls.
- Leave test rows in the DB for the user to inspect unless told otherwise.
