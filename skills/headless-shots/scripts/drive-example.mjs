// Drive two save scenarios through headless Chrome CDP. Usage: node drive.mjs <token> <outdir> <editProductId>
import { spawn } from "node:child_process";
import { writeFileSync } from "node:fs";

const [token, outDir, editId] = process.argv.slice(2);
const port = 9334;
const chrome = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", [
  "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
  `--remote-debugging-port=${port}`, "--user-data-dir=/tmp/claude-501/chrome-prof2", "--window-size=1440,900", "about:blank",
], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
for (let i = 0; i < 40; i++) { try { await fetch(`http://127.0.0.1:${port}/json/version`); break; } catch { await sleep(250); } }
let id = 0; const pending = new Map();
const target = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: "PUT" })).json();
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));
ws.onmessage = (e) => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.rej(new Error(JSON.stringify(m.error))) : p.res(m.result); } };
const call = (method, params = {}) => new Promise((res, rej) => { const n = ++id; pending.set(n, { res, rej }); ws.send(JSON.stringify({ id: n, method, params })); });
const evalJs = async (expression) => { const r = await call("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true }); if (r.exceptionDetails) throw new Error(r.exceptionDetails.text + " " + JSON.stringify(r.exceptionDetails.exception?.description)); return r.result.value; };
const shot = async (name) => { const s = await call("Page.captureScreenshot", { format: "png" }); writeFileSync(`${outDir}/${name}.png`, Buffer.from(s.data, "base64")); };
const goto = async (p) => { await call("Page.navigate", { url: `http://localhost:3000${p}` }); await sleep(2500); };

await call("Network.enable");
await call("Network.setCookie", { name: "sparktoy_session", value: token, domain: "localhost", path: "/", httpOnly: true });
await call("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });

// helper injected into pages: React-safe setters
const helpers = `
  window.__setInput = (el, v) => { const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, v); el.dispatchEvent(new Event('input', { bubbles: true })); };
  window.__setSelect = (el, v) => { Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set.call(el, v); el.dispatchEvent(new Event('change', { bubbles: true })); };
  window.__byLabel = (txt) => { const lab = [...document.querySelectorAll('label')].find(l => l.textContent.trim().startsWith(txt)); if (!lab) return null;
    const wrap = lab.parentElement; return wrap.querySelector('input, select, textarea'); };
  window.__btn = (txt) => [...document.querySelectorAll('button')].find(b => b.textContent.trim() === txt);
  true`;

// ── A. edit: 套用 百貨價 建議 → 儲存變更
await goto(`/products/${editId}`);
await evalJs(helpers);
const applied = await evalJs(`(() => { const b = window.__btn('套用'); if (!b) return 'no-apply-btn'; b.click(); return 'clicked'; })()`);
await sleep(300);
const deptVal = await evalJs(`(() => { const row = [...document.querySelectorAll('tr')].find(r => r.textContent.includes('百貨價')); return row ? row.querySelector('input')?.value : 'no-row'; })()`);
console.log("A: apply =", applied, "| 百貨價 input =", deptVal);
await evalJs(`(() => { window.__btn('儲存變更').click(); return true; })()`);
await sleep(4000);
const urlA = await evalJs("location.pathname");
const errA = await evalJs(`(document.querySelector('p.text-red-600')?.textContent || '').slice(0, 200)`);
console.log("A: after save url =", urlA, "| error =", JSON.stringify(errA));
await shot("A_after_save");

// ── B. create: 品名 + 供應商 + 條碼 → 建立商品
await goto("/products/new");
await evalJs(helpers);
const setup = await evalJs(`(() => {
  const name = window.__byLabel('商品品名'); if (!name) return 'no-name';
  window.__setInput(name, 'QA 自動測試 條碼建檔 ${Date.now()}');
  const sup = window.__byLabel('供應商'); if (!sup || sup.tagName !== 'SELECT') return 'no-supplier-select';
  const opt = [...sup.options].find(o => o.value); if (!opt) return 'no-supplier-option';
  window.__setSelect(sup, opt.value);
  const bc = window.__byLabel('條碼'); if (!bc) return 'no-barcode';
  window.__setInput(bc, '4710000QA0001');
  return 'ok:' + opt.textContent.trim();
})()`);
console.log("B: setup =", setup);
await sleep(300);
await evalJs(`(() => { window.__btn('建立商品').click(); return true; })()`);
await sleep(4000);
const urlB = await evalJs("location.pathname");
const errB = await evalJs(`(document.querySelector('p.text-red-600')?.textContent || '').slice(0, 200)`);
console.log("B: after create url =", urlB, "| error =", JSON.stringify(errB));
await shot("B_after_create");

ws.close(); chrome.kill();
