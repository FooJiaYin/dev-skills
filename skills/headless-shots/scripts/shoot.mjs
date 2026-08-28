// Headless Chrome + CDP screenshots with a session cookie. Usage: node shoot.mjs <token> <outdir> <path>...
import { spawn } from "node:child_process";
import { writeFileSync } from "node:fs";

const [token, outDir, ...paths] = process.argv.slice(2);
const port = 9333;
const chrome = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", [
  "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
  `--remote-debugging-port=${port}`, "--user-data-dir=/tmp/claude-501/chrome-prof", "--window-size=1440,900", "about:blank",
], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
for (let i = 0; i < 40; i++) { try { await fetch(`http://127.0.0.1:${port}/json/version`); break; } catch { await sleep(250); } }

let id = 0; const pending = new Map();
function call(ws, method, params = {}) {
  return new Promise((res, rej) => { const n = ++id; pending.set(n, { res, rej }); ws.send(JSON.stringify({ id: n, method, params })); });
}
const target = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: "PUT" })).json();
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));
ws.onmessage = (e) => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.rej(new Error(JSON.stringify(m.error))) : p.res(m.result); } };

await call(ws, "Network.enable");
await call(ws, "Network.setCookie", { name: "sparktoy_session", value: token, domain: "localhost", path: "/", httpOnly: true });
await call(ws, "Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
for (const p of paths) {
  await call(ws, "Page.navigate", { url: `http://localhost:3000${p}` });
  await sleep(2500);
  const { result } = await call(ws, "Runtime.evaluate", { expression: "document.documentElement.scrollHeight" });
  const h = Math.min(Math.max(result.value || 900, 900), 6000);
  await call(ws, "Emulation.setDeviceMetricsOverride", { width: 1440, height: h, deviceScaleFactor: 1, mobile: false });
  await sleep(300);
  const shot = await call(ws, "Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
  const name = p.replace(/[^a-z0-9]+/gi, "_").replace(/^_|_$/g, "") || "root";
  writeFileSync(`${outDir}/${name}.png`, Buffer.from(shot.data, "base64"));
  console.log(`${p} -> ${name}.png (h=${h})`);
  await call(ws, "Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
}
ws.close(); chrome.kill();
