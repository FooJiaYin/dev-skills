// 視窗大小截圖＋捲動／滑鼠步驟（響應式、捲動動畫、hover 互動）。
// Usage: node steps.mjs <url> <outPrefix> <width> <height> <mobile 0|1> '<steps json>'
// steps: [{ "js": "scrollTo(0, 900)", "mouse": [x, y], "wait": ms, "shot": "name" }, ...]（每步可只填部分欄位）
// 每步 js 的回傳值會印出；查水平溢出可在最後放 {"js":"JSON.stringify({sw:document.documentElement.scrollWidth,iw:innerWidth})"}
// 頁面有 scroll-behavior: smooth 時，第一步先 document.documentElement.style.scrollBehavior='auto'，否則 scrollTo 後立刻截圖還停在原處
import { spawn } from "node:child_process";
import { writeFileSync } from "node:fs";
import { tmpdir } from "node:os";

const [url, out, w, h, mobile, stepsJson] = process.argv.slice(2);
const W = +w, H = +h, M = mobile === "1";
const port = 9300 + Math.floor(Math.random() * 500);
const chrome = spawn(process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", [
  "--headless=new", "--hide-scrollbars", "--no-first-run", "--autoplay-policy=no-user-gesture-required",
  `--remote-debugging-port=${port}`, `--user-data-dir=${tmpdir()}/headless-steps-${port}`, `--window-size=${W},${H}`, "about:blank",
], { stdio: "ignore" });
for (const sig of ["exit", "SIGINT", "SIGTERM", "SIGHUP"]) process.on(sig, () => { try { chrome.kill("SIGKILL"); } catch {} if (sig !== "exit") process.exit(130); });
setTimeout(() => process.exit(3), 180000);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
for (let i = 0; i < 120; i++) { try { await fetch(`http://127.0.0.1:${port}/json/version`); break; } catch { await sleep(250); } }

let id = 0; const pending = new Map();
const call = (method, params = {}) => new Promise((res) => { const n = ++id; pending.set(n, res); ws.send(JSON.stringify({ id: n, method, params })); });
const target = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: "PUT" })).json();
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));
ws.onmessage = (e) => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m.result || m); pending.delete(m.id); } };

await call("Emulation.setDeviceMetricsOverride", { width: W, height: H, deviceScaleFactor: 1, mobile: M });
if (M) await call("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 1 });
await call("Page.navigate", { url });
await sleep(1500);
for (const s of JSON.parse(stepsJson)) {
  if (s.js) {
    const r = await call("Runtime.evaluate", { expression: s.js, awaitPromise: true, returnByValue: true });
    if (r.exceptionDetails) console.log("ERR", r.exceptionDetails.exception?.description);
    else if (r.result?.value !== undefined) console.log(JSON.stringify(r.result.value));
  }
  if (s.mouse) await call("Input.dispatchMouseEvent", { type: "mouseMoved", x: s.mouse[0], y: s.mouse[1] });
  if (s.wait) await sleep(s.wait);
  if (s.shot) {
    const r = await call("Page.captureScreenshot", { format: "jpeg", quality: 70 });
    writeFileSync(`${out}-${s.shot}.jpg`, Buffer.from(r.data, "base64"));
    console.log("shot", s.shot);
  }
}
process.exit(0);
