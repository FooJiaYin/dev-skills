# Plaud share URL — extraction recipe

Triggered when the input URL matches `web.plaud.ai/s/pub_<uuid>`.

## Why Playwright (and not curl / WebFetch)

Plaud share pages are JavaScript-rendered SPAs. The public API path `api.plaud.ai/file/share-content/<id>` returns `{"status":-1,"msg":"链接错误"}` for unauthenticated shares regardless of header tricks. **Don't try variations — go straight to Playwright.**

## Flow

### 1. Navigate

```text
mcp__plugin_playwright_playwright__browser_navigate(url)
mcp__plugin_playwright_playwright__browser_wait_for(time=3)
```

The outer URL embeds an iframe pointing at `web.plaud.ai/nshare/pub_<uuid>`; same-origin so `iframe.contentDocument` works.

### 2. Switch to the Transcript tab

Plaud opens on **Summary** by default — not what we want. Click the Transcript tab:

```js
() => {
  const iframe = document.querySelector('iframe');
  const doc = iframe.contentDocument;
  for (const el of doc.querySelectorAll('*')) {
    if (el.children.length === 0 && (el.textContent || '').trim() === 'Transcript') {
      el.click();
      return true;
    }
  }
  return false;
}
```

Then `browser_wait_for(time=2)` to let the tab render.

### 3. Dump iframe innerText

```js
() => document.querySelector('iframe').contentDocument.body.innerText
```

> **No trailing semicolon.** `browser_evaluate` wraps the arrow function as an expression — a `;` at the end produces `SyntaxError: Unexpected token ';'`.

Save via `browser_evaluate`'s `filename` param to `.playwright-mcp/plaud_raw.txt` (relative to workspace root). An absolute path is fine **as long as it resolves inside the workspace root** — `/tmp/...` and other outside-workspace paths are rejected.

### 4. Clean the dump

The result is JSON-encoded (one giant line) and begins with cookie banner + metadata, up to the marker `00:00:00/ <duration>`. Strip everything before that marker and write the cleaned transcript **directly to the meetings folder** (so it's preserved alongside the meeting note):

```bash
python3 - <<'PY'
import json, pathlib, os
p = pathlib.Path('.playwright-mcp/plaud_raw.txt')
text = json.loads(p.read_text())
lines = text.split('\n')
start = next((i+1 for i, l in enumerate(lines) if l.strip().startswith('00:00:00/')), 0)
# Replace <date>-<title> with the resolved metadata from §5 before running
out = pathlib.Path('docs/meetings/<date>-<title>-transcript.txt')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('\n'.join(lines[start:]))
PY
```

The cleaned transcript for a 2-hour meeting is ~45 KB / ~1700 lines. Use `Read` with `offset` + `limit` to page through — a single `Read` will exceed the 25k token limit.

### 5. Grab metadata from the raw dump

Before the marker line, the dump contains:

- **Title** — `<title>` of the page (also visible in the header)
- **Date + time** — `YYYY-MM-DD HH:MM:SS` line
- **Duration** — `Nh Nm Ns` line

Hand these to §3 of the main SKILL.md.

### 6. Cleanup (ask first, never auto-delete)

After the meeting note is saved, **the cleaned transcript already lives in `docs/meetings/<date>-<title>-transcript.txt`** (from §4) — it's preserved by design.

The only thing that may need clearing is `.playwright-mcp/plaud_raw.txt` (the intermediate JSON dump). Ask the user via `AskUserQuestion`:

- Question: "Delete the intermediate Plaud raw dump (`.playwright-mcp/plaud_raw.txt`)? The cleaned transcript is already in `docs/meetings/`."
- Options:
  1. **Yes, delete** — `rm .playwright-mcp/plaud_raw.txt`
  2. **No, keep it** (default) — leave the raw dump in place for re-processing

Then close the browser: `mcp__plugin_playwright_playwright__browser_close()`.

## Failure modes & recovery

- **`{"status":-1,"msg":"链接错误"}` from `api.plaud.ai`** — confirms the API is dead for unauth shares. Go straight to Playwright, don't loop on variations.
- **`browser_navigate` returns "Error: Stream closed"** — Playwright MCP not ready. Retry the same call once; if it still fails, ask the user to confirm Playwright is installed.
- **`File access denied: /tmp/...`** — `browser_evaluate`'s `filename` must be inside the workspace. Use `<workspace>/.playwright-mcp/<name>.txt`.
- **`Read` fails with "exceeds maximum allowed tokens"** — run step 4 (clean) first; then page the cleaned file (now in `docs/meetings/<date>-<title>-transcript.txt`) with `offset`/`limit`.
- **Tab click does nothing** — the SPA re-rendered. Re-query the DOM (don't cache element refs across waits) and click again.
