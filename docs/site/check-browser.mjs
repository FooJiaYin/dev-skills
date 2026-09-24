// Adapted from skills/headless-shots/scripts/shoot.mjs.
// No login, app writes or network services: verify the local static demo only.
import { spawn } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { fileURLToPath } from "node:url";
import path from "node:path";
import assert from "node:assert/strict";

const profile = mkdtempSync(path.join(tmpdir(), "dev-skills-demo-check-"));
const shots = mkdtempSync(path.join(tmpdir(), "dev-skills-demo-shots-"));
const chrome = spawn(process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", [
  "--headless=new", "--disable-gpu", "--no-first-run", "--remote-debugging-port=0",
  "--user-data-dir=" + profile, "about:blank"
], { stdio: "ignore" });
let launchError;
chrome.on("error", error => { launchError = error; });
const deadline = setTimeout(() => { chrome.kill(); console.error("Browser check timed out"); process.exit(2); }, 55000);
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
let ws;
try {
  let port;
  for (let i = 0; i < 60; i++) {
    if (launchError) throw launchError;
    if (chrome.exitCode !== null) throw Error("Chrome exited before exposing CDP; launch may require sandbox approval");
    try { port = readFileSync(path.join(profile, "DevToolsActivePort"), "utf8").split("\n")[0]; break; } catch { await sleep(150); }
  }
  assert(port, "Chrome ready");
  const target = await (await fetch("http://127.0.0.1:" + port + "/json/new?about:blank", { method: "PUT" })).json();
  ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
  let id = 0;
  const pending = new Map(), errors = [];
  ws.onmessage = event => {
    const message = JSON.parse(event.data);
    if (message.method === "Runtime.exceptionThrown") errors.push(message.params.exceptionDetails);
    if (pending.has(message.id)) {
      const p = pending.get(message.id); pending.delete(message.id);
      message.error ? p.reject(message.error) : p.resolve(message.result);
    }
  };
  const call = (method, params = {}) => new Promise((resolve, reject) => {
    const n = ++id; pending.set(n, { resolve, reject }); ws.send(JSON.stringify({ id: n, method, params }));
  });
  const evaluate = async expression => {
    const result = await call("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
    if (result.exceptionDetails) throw Error(JSON.stringify(result.exceptionDetails));
    return result.result.value;
  };
  const until = async (expression, timeout = 9000) => {
    const end = Date.now() + timeout;
    while (Date.now() < end) { if (await evaluate(expression)) return; await sleep(70); }
    throw Error("Condition timed out: " + expression);
  };
  await call("Runtime.enable");
  await call("Page.enable");
  await call("Emulation.setDeviceMetricsOverride", { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false });
  await call("Page.navigate", { url: new URL("./index.html", import.meta.url).href });
  await until("document.querySelectorAll('.demo-scene').length === 8");
  assert(await evaluate("['prd', 'spec', 'spec-review', 'headless-shots'].every(id => !window.DEV_SKILLS_DEMOS[id] && !document.getElementById('demo-' + id))"), "excluded skills are not loaded or rendered");
  assert.equal(await evaluate("document.querySelectorAll('#claude-chat .chat-entry').length"), 0);
  assert.equal(await evaluate("document.querySelectorAll('.chat-choice, [data-choice], [data-conversation]').length"), 0);
  assert.equal(await evaluate("document.querySelectorAll('[role=tab]').length"), 1);
  assert.equal(await evaluate("document.querySelectorAll('.wrap-mode').length"), 2);
  assert.deepEqual(await evaluate("[...document.querySelectorAll('.wrap-mode--quick .mode-step--skipped code')].map(el => el.textContent)"), ["/verify", "/update-docs", "/code-review", "deploy → /improve"]);
  assert(await evaluate("[...document.querySelectorAll('.wrap-mode--quick .mode-step--skipped')].every(el => el.querySelector('s') && !el.querySelector('span'))"), "Quick omitted steps are struck through without descriptions");
  assert(await evaluate("[...document.querySelectorAll('.wrap-mode--full .mode-steps li')].filter(el => ['/report → /rename-session','cleanup + commit','/sync-report'].includes(el.querySelector('code').textContent)).every(el => !el.querySelector('span'))"), "Full avoids repeating shared step descriptions");
  assert.equal(await evaluate("document.querySelector('[data-method-stage=delivery] .delivery-trunk > b').textContent"), "cleanup + commit", "the version step names /wrap-up's cleanup and commit work");
  assert.deepEqual(await evaluate("[...document.querySelectorAll('.demo-scene')].map(section => section.dataset.scenePanel)"), ["setup-notion", "meeting-notes", "sync", "wrap-up", "verify", "report", "find-session", "improve"], "six methods with setup and separate memory architecture");
  assert.equal(await evaluate("document.querySelectorAll('.demo-input, .demo-reason').length"), 0, "redundant explanation blocks removed");
  assert.equal(await evaluate("document.querySelectorAll('#demo-wrap-up .document-preview, #demo-wrap-up .wrap-picture').length"), 0, "wrap-up has no duplicate overview or document previews");
  assert(await evaluate("document.querySelector('.wrap-mode--full').getBoundingClientRect().left > document.querySelector('.wrap-mode--quick').getBoundingClientRect().right"), "Quick and Full sit side by side");
  assert(await evaluate("Math.abs(document.querySelector('.wrap-mode--full').getBoundingClientRect().height - document.querySelector('.wrap-mode--quick').getBoundingClientRect().height) < 1"), "Quick and Full have equal height");
  assert.equal(await evaluate("document.querySelectorAll('#demo-sync .flow-visual .flow-node').length"), 3, "sync uses the original connected three-node design");
  assert.equal(await evaluate("document.querySelectorAll('#demo-sync .flow-connector').length"), 2, "sync restores fetch/merge arrow connectors");
  assert.equal(await evaluate("document.querySelectorAll('#demo-sync .sync-branches').length"), 0, "sync branch redesign is undone");
  assert.equal(await evaluate("document.querySelectorAll('#demo-verify .verify-cycle > li').length"), 3, "verify runs tests, fixes failures, and reruns");
  assert.equal(await evaluate("document.querySelectorAll('#demo-verify [data-demo-document=verify]').length"), 0, "verify does not offer an invented checklist file");
  assert(await evaluate("document.querySelector('#demo-verify .document-preview').dataset.previewDocument === 'discuss'"), "verify references the existing plan as input");
  assert.equal(await evaluate("document.querySelectorAll('#demo-report .handoff-rail > .method-stage').length"), 4, "report and automatic naming share one handoff step");
  assert.equal(await evaluate("document.querySelectorAll('#demo-report [data-method-stage=rename-session]').length"), 0);
  assert(await evaluate("document.querySelector('#demo-report [data-method-stage=report] h3').textContent.includes('/report') && document.querySelector('#demo-report [data-method-stage=report] h3').textContent.includes('/rename-session')"), "one result step identifies both skills");
  assert(await evaluate("getComputedStyle(document.querySelector('#demo-setup-notion .tone-mint')).backgroundColor === getComputedStyle(document.querySelector('#demo-setup-notion .tone-blue')).backgroundColor"), "setup uses neutral squares with differentiated icons");
  assert(await evaluate("[...document.querySelectorAll('.demo-scene .picture-node, .demo-scene .flow-node')].every(node => { const rect = node.getBoundingClientRect(); return Math.abs(rect.width - rect.height) < 1 && getComputedStyle(node).display === 'grid'; })"), "small diagram nodes are squares, not flex panels");
  assert.equal(await evaluate("document.querySelectorAll('.method-review-team .role-card').length"), 6);
  assert.equal(await evaluate("document.querySelectorAll('.file[data-scene]').length"), 17);
  assert.equal(await evaluate("document.querySelector('.demo-scene').dataset.scenePanel"), "setup-notion");
  assert.equal(await evaluate("document.querySelector('#demo-files .file').dataset.scene"), "setup-notion");
  assert.equal(await evaluate("document.querySelectorAll('.demo-artifact').length"), 0);
  assert.equal(await evaluate("document.querySelectorAll('[data-demo-replay]').length"), 4);
  assert(await evaluate("[...document.querySelectorAll('.playback-cta')].every(button => button.dataset.demoReplay === 'install' || (button.querySelector('.cta-skill')?.textContent || '').startsWith('/'))"), "skill playback CTAs name their skill; installation is a separate demo");
  assert(await evaluate("document.querySelector('[data-method-play=delivery] .cta-skill').textContent === '/wrap-up' && document.querySelector('[data-method-play=resume] .cta-skill').textContent === '/find-session' && document.querySelector('[data-play-stage=meeting-notes] .cta-skill').textContent === '/meeting-notes'"), "process-only stages name the skill they demonstrate");
  assert.equal(await evaluate("document.querySelectorAll('#demo-meeting-notes [data-play-stage=transcript]').length"), 0, "the transcript is input, not a duplicate /meeting-notes action");
  assert.equal(await evaluate("document.querySelectorAll('#demo-meeting-notes [data-play-stage=meeting-notes]').length"), 1, "the note conversion has one /meeting-notes action");
  assert.equal(await evaluate("new Set([...document.querySelectorAll('[data-demo-replay]')].map(button => button.textContent.trim())).size"), 4, "sections and installation have distinct playback invitations");
  assert.equal(await evaluate("new Set([...document.querySelectorAll('[data-demo-replay]')].map(button => getComputedStyle(button).backgroundColor)).size >= 2"), true, "sections use distinct CTA color roles");
  assert(await evaluate("[...document.querySelectorAll('#demo-setup-notion .scene__content, #demo-wrap-up .scene__content, #demo-improve .scene__content')].every(e => e.lastElementChild.classList.contains('section-actions'))"), "remaining sections keep bottom CTAs");
  assert.equal(await evaluate("document.querySelectorAll('#demo-meeting-notes .section-actions, #demo-sync .section-actions, #demo-verify .section-actions, #demo-report .section-actions, #demo-find-session .section-actions').length"), 0, "method flows do not repeat step and document actions in footer rows");
  assert.equal(await evaluate("document.querySelectorAll('#demo-meeting-notes [data-meeting-step]').length"), 5);
  assert.equal(await evaluate("document.querySelectorAll('#demo-meeting-notes .skill-visual').length"), 1, "one information-to-work diagram, not separate skill sections");
  assert.equal(await evaluate("document.querySelectorAll('#demo-meeting-notes .meeting-flow-node').length"), 4);
  assert(await evaluate("document.querySelector('.titlebar__title').textContent.includes('foojiayin')"));
  assert(await evaluate("[...document.querySelectorAll('.skill-related')].every(group => group.hidden)"));
  assert(await evaluate("getComputedStyle(document.querySelector('.chat-ready')).display !== 'none'"));
  assert.deepEqual(await evaluate("[...document.querySelectorAll('.chat-lifecycle [data-stage]')].map(e => e.textContent)"), ["Source", "Prepare", "Wrap-up", "Memory"]);
  assert(await evaluate("document.querySelectorAll('#story-panel h2 .title-type-glyph').length > 0 && document.querySelectorAll('#story-panel h1 .title-type-glyph, #story-panel h3 .title-type-glyph').length === 0"), "only large white headings type");
  await evaluate("document.querySelector('#why-title').scrollIntoView({block:'center'})");
  await until("[...document.querySelectorAll('#why-title .title-type-glyph')].every(glyph => getComputedStyle(glyph).visibility === 'visible')", 4000);
  assert(await evaluate("[...document.querySelectorAll('.skill-name')].every(e => e.textContent.startsWith('/'))"));
  assert(await evaluate("[...document.querySelectorAll('[data-scene]:not([data-scene=welcome])')].every(e => e.textContent.includes('/' + e.dataset.scene))"));
  assert(await evaluate("[...document.querySelectorAll('[data-scene]:not([data-scene=welcome])')].every(e => e.querySelector('.file__icon--skill'))"));
  assert.equal(await evaluate("document.querySelectorAll('[data-scene=wrap-up]').length"), 1);
  assert.equal(await evaluate("document.querySelectorAll('.explorer-shortcuts [data-scene=wrap-up]').length"), 0);
  assert.deepEqual(await evaluate("[...document.querySelectorAll('[data-skill-folder=wrap-up] .skill-folder__children [data-scene]')].map(e => e.dataset.scene)"), ["verify", "update-docs", "code-review", "report", "rename-session", "sync-report", "improve"]);
  assert.equal(await evaluate("new Set([...document.querySelectorAll('[data-scene]')].map(e => e.dataset.scene)).size"), 17, "no duplicated skill entries");
  assert(await evaluate("[...document.querySelectorAll('.demo-scene:not(#demo-wrap-up):not(#demo-improve)')].every(section => section.querySelector('[data-demo-document]:not([target])'))"));
  assert.equal(await evaluate("document.querySelectorAll('#demo-improve [data-demo-document]').length"), 0, "Improve suggestions stay in chat, not a document");
  assert.equal(await evaluate("document.querySelectorAll('#demo-wrap-up [data-demo-document], [data-method-stage=sync] [data-demo-document], [data-method-stage=rename-session] [data-demo-document], [data-method-stage=delivery] [data-demo-document]').length"), 0, "steps without documents do not invent file CTAs");
  assert(await evaluate("[...document.querySelectorAll('.method-actions button, .section-cta--replay')].every(button => button.classList.contains('playback-cta') && button.querySelector('svg')) && [...document.querySelectorAll('.meeting-step-actions button')].every(button => button.classList.contains('playback-cta') && button.textContent.trim().startsWith('試試 /'))"), "playback uses the prominent CTA and meeting steps say 試試 /skill");
  assert(await evaluate("document.querySelectorAll('.document-preview').length >= 5"));
  assert.equal(await evaluate("document.querySelectorAll('.lifecycle-main-path .lifecycle-node').length"), 4);
  assert.equal(await evaluate("document.querySelectorAll('.github-branch-path .branch-node').length"), 3);
  assert.equal(await evaluate("document.querySelectorAll('#demo-wrap-up .skill-visual').length"), 0, "wrap-up uses the two timelines instead of a duplicate diagram");
  assert.equal(await evaluate("document.querySelectorAll('.method-layout').length"), 5, "prepare, quality, handoff, memory and improvement have dedicated compositions");
  assert.deepEqual(await evaluate("[...document.querySelectorAll('#install .install-method > div:first-child .install-commands code')].map(el => el.textContent)"), ["/plugin marketplace add FooJiaYin/dev-skills", "/plugin install dev-skills"], "ending shows the real Claude Code install sequence");
  assert.deepEqual(await evaluate("[...document.querySelectorAll('#install .install-method > div:last-child .install-commands code')].map(el => el.textContent)"), ["git clone https://github.com/FooJiaYin/dev-skills.git ~/dev-skills", "mkdir -p ~/.codex/skills", 'for skill in ~/dev-skills/skills/*; do ln -s "$skill" ~/.codex/skills/; done'], "ending gives Codex runnable clone and safe symlink commands");
  assert.equal(await evaluate("document.querySelector('#install .install-download').dataset.demoReplay"), "install", "ending opens a simulated installation conversation, not a ZIP download");
  assert(await evaluate("document.querySelector('#install .install-readme').href.endsWith('/dev-skills#install')"), "complete installation guide remains available");
  assert.equal(await evaluate("document.querySelectorAll('.handoff-summary__track > div').length"), 3, "handoff shows three distinct report outcomes");
  assert.equal(await evaluate("document.querySelectorAll('#claude-chat [data-route]').length"), 0);
  assert(await evaluate("!document.querySelector('#story-panel').innerText.includes('琢奧')"), "project name stays outside the narrative");
  assert(await evaluate("!document.querySelector('.statusbar').innerText.includes('琢奧')"));
  const scrollTo = async name => {
    await evaluate("(() => { const s = document.querySelector('.editor__scroll'); const p = document.getElementById(" + JSON.stringify(name === "welcome" ? "welcome" : "demo-" + name) + "); s.scrollTo({top:s.scrollTop + p.getBoundingClientRect().top - s.getBoundingClientRect().top, behavior:'instant'}); })()");
    await sleep(90);
    const distance = await evaluate("document.getElementById(" + JSON.stringify(name === "welcome" ? "welcome" : "demo-" + name) + ").getBoundingClientRect().top - document.querySelector('.editor__scroll').getBoundingClientRect().top");
    assert(Math.abs(distance) < 2, "scroll target must align: " + name + " (" + distance + ")");
  };
  // Real animation, including an automatically answered question. No clicking.
  await scrollTo("setup-notion");
  await until("document.querySelector('#claude-chat .chat-compose.is-composing') !== null");
  assert.equal(await evaluate("document.querySelectorAll('#claude-chat [data-role=user]').length"), 0, "user text starts in the composer, not in a chat bubble");
  await until("document.querySelector('#claude-chat .is-typing') !== null");
  await until("document.querySelector('#claude-chat .chat-complete').disabled");
  assert.equal(await evaluate("document.querySelectorAll('#claude-chat [data-role=user]').length"), 1, "selecting an answer does not type another user message");
  assert.equal(await evaluate("document.querySelectorAll('#claude-chat .chat-entry').length"), await evaluate("window.DEV_SKILLS_DEMOS['setup-notion'].messages.length - 1"));
  assert.deepEqual(await evaluate("[...document.querySelectorAll('#claude-chat [data-role=question] .question-option')].map(button => button.textContent)"), ["沿用", "另外提供"], "agent confirmation uses visible option buttons");
  assert.equal(await evaluate("document.querySelector('#claude-chat [data-role=question] .question-option.is-selected').textContent"), "沿用", "automatic reply visibly selects its option");
  assert.equal(await evaluate("document.querySelectorAll('#claude-chat .chat-document-chip[data-demo-document=setup-notion]').length"), 1);
  assert.equal(await evaluate("document.querySelectorAll('#claude-chat [data-role=assistant] .chat-bubble .chat-document-chip').length"), 1, "file chips are inside the assistant bubble");
  await evaluate("document.querySelector('#claude-chat .chat-document-chip').click()");
  assert.equal(await evaluate("document.querySelector('[role=tab][aria-selected=true]').id"), "tab-setup-notion");
  await evaluate("document.querySelector('.editor-tab-close').click()");
  assert(await evaluate("document.querySelector('#claude-chat [data-role=skill] .skill-command').textContent === '/setup-notion'"));
  assert(await evaluate("document.querySelector('#claude-chat [data-role=skill]').classList.contains('chat-entry--tool')"));
  assert.equal(await evaluate("getComputedStyle(document.querySelector('#claude-chat [data-role=skill]')).backgroundColor"), "rgba(0, 0, 0, 0)");
  assert.equal(await evaluate("getComputedStyle(document.querySelector('#claude-chat [data-role=skill] .skill-command')).color"), await evaluate("getComputedStyle(document.querySelector('#claude-chat [data-role=user] .skill-command')).color"));
  await evaluate("(() => { const picker = document.querySelector('#claude-chat [data-host-picker]'); picker.value = 'codex'; picker.dispatchEvent(new Event('change')); })()");
  assert(await evaluate("[...document.querySelectorAll('[data-assistant-name]')].every(e => e.textContent === 'Codex')"));
  assert.equal(await evaluate("document.querySelectorAll('#claude-chat .chat-entry').length"), await evaluate("window.DEV_SKILLS_DEMOS['setup-notion'].messages.length - 1"), "host switch does not restart");
  await scrollTo("sync");
  await scrollTo("setup-notion");
  await until("document.querySelector('#claude-chat .is-typing') !== null");
  assert(await evaluate("document.querySelectorAll('#claude-chat .chat-entry').length < window.DEV_SKILLS_DEMOS['setup-notion'].messages.length"), "scroll return replays from start");
  await evaluate("document.querySelector('[data-demo-replay=setup-notion]').click()");
  await until("document.querySelector('#claude-chat .is-typing') !== null");
  assert(await evaluate("document.querySelectorAll('#claude-chat .chat-entry').length < window.DEV_SKILLS_DEMOS['setup-notion'].messages.length"), "CTA resets completed conversation");
  // Scrolling back cancels pending typing.
  await scrollTo("sync");
  await scrollTo("meeting-notes");
  assert.equal(await evaluate("document.querySelectorAll('.preview-study').length"), 0);
  assert(await evaluate("[...document.querySelectorAll('.document-preview')].every(card => getComputedStyle(card).borderTopLeftRadius === '4px' && getComputedStyle(card, '::before').backgroundImage.includes('linear-gradient'))"), "previews use a small radius and folded corner");
  assert(await evaluate("[...document.querySelectorAll('.document-preview-open')].every(link => link.textContent.trim() === '查看文件 ↗')"), "preview CTA labels are consistent");
  assert(await evaluate("[...document.querySelectorAll('.document-preview-open')].every(link => getComputedStyle(link).display === 'flex' && Math.abs(link.getBoundingClientRect().width - (link.closest('.document-preview').getBoundingClientRect().width - 24)) < 1)"), "floating buttons span the card width with equal side padding");
  assert(await evaluate("[...document.querySelectorAll('.demo-scene .document-preview')].every(card => card.getBoundingClientRect().height === 248)"), "all document preview cards have the same height");
  assert.deepEqual(await evaluate("[...document.querySelectorAll('#demo-report .preview-line-number')].slice(0, 5).map(el => el.textContent)"), ["0", "1", "2", "3", "4"]);
  assert.equal(await evaluate("document.querySelectorAll('.meeting-step-actions [data-play-stage]').length"), 4);
  assert.equal(await evaluate("document.querySelectorAll('.meeting-workflow .stage-view').length"), 5);
  assert.equal(await evaluate("document.querySelectorAll('.meeting-flow .meeting-preview').length"), 4);
  assert.equal(await evaluate("document.querySelectorAll('.meeting-preview .skill-name').length"), 0, "file previews never label files with skill names");
  assert.deepEqual(await evaluate("[...document.querySelectorAll('.meeting-preview figcaption b')].map(el => el.textContent)"), ["逐字稿.txt", "會議記錄.md", "任務建立紀錄.md", "task.md"]);
  assert(await evaluate("[...document.querySelectorAll('.meeting-preview')].every(card => getComputedStyle(card.querySelector('.document-preview-excerpt'), '::after').backgroundImage.includes('linear-gradient') && card.querySelector('.stage-view').getBoundingClientRect().top < card.querySelector('.document-preview-excerpt').getBoundingClientRect().bottom && card.querySelector('.stage-view').getBoundingClientRect().bottom <= card.getBoundingClientRect().bottom)"), "preview buttons float over the bottom gradient within their cards");
  for (const stage of ["meeting-notes", "upload-meeting", "create-tasks", "fetch-task"]) {
    await evaluate("document.querySelector('[data-play-stage=" + stage + "]').click()");
    await until("document.querySelector('.meeting-workflow').dataset.currentStage === " + JSON.stringify(stage));
    await evaluate("document.querySelector('.chat-pause').click()");
    const frameBefore = await evaluate("JSON.stringify([...document.querySelectorAll('[data-meeting-step]')].map(el => el.dataset.flowState))");
    await sleep(200);
    assert.equal(await evaluate("JSON.stringify([...document.querySelectorAll('[data-meeting-step]')].map(el => el.dataset.flowState))"), frameBefore, "pausing chat also pauses workflow progress");
    const docId = stage === "transcript" ? "meeting-transcript" : stage;
    await evaluate("document.querySelector('[data-meeting-step=" + stage + "] .stage-view').click()");
    assert.equal(await evaluate("document.querySelector('[role=tab][aria-selected=true]').id"), "tab-" + docId, "every stage opens its own IDE document");
    await evaluate("document.querySelector('.editor-tab-close').click()");
    assert.equal(await evaluate("JSON.stringify([...document.querySelectorAll('[data-meeting-step]')].map(el => el.dataset.flowState))"), frameBefore, "viewing documents does not restart or advance playback");
  }
  await evaluate("document.querySelector('[data-play-stage=create-tasks]').click()");
  await until("document.querySelector('[data-meeting-step=create-tasks]').dataset.flowState === 'preview'");
  await evaluate("document.querySelector('.chat-pause').click()");
  assert.equal(await evaluate("document.querySelector('[data-task-write-status]').textContent"), "候選任務 · 尚未寫入", "candidate tasks are not presented as already created");
  await evaluate("document.querySelector('.chat-complete').click()");
  assert(await evaluate("[...document.querySelectorAll('[data-meeting-step]')].every(el => el.dataset.flowState === 'done')"), "complete reveals every accumulated result");
  assert.equal(await evaluate("document.querySelector('[data-task-write-status]').textContent"), "Notion 寫入完成");
  const completedHeight = await evaluate("document.querySelector('.meeting-flow').getBoundingClientRect().height");
  await evaluate("document.querySelector('[data-inline-replay=meeting-notes]').click()");
  await until("document.querySelector('.meeting-workflow').dataset.currentStage === 'transcript'");
  assert.equal(await evaluate("document.querySelector('[data-meeting-step=fetch-task]').dataset.flowState"), "waiting", "replay removes future outcomes");
  assert.equal(await evaluate("document.querySelector('.meeting-flow').getBoundingClientRect().height"), completedHeight, "revealing outcomes does not jump the article layout");
  assert(await evaluate("[...document.querySelectorAll('.meeting-workflow .skill-name')].every(el => getComputedStyle(el).color === getComputedStyle(document.querySelector('.workflow-name')).color)"), "skill labels stay orange regardless of playback state");
  assert(await evaluate("[...document.querySelectorAll('.meeting-flow-node h3 code')].every(node => getComputedStyle(node).whiteSpace === 'nowrap' && node.scrollWidth <= node.clientWidth + 1)"), "skill step titles stay complete on one line");
  assert(await evaluate("(() => { const rows = [...document.querySelectorAll('.meeting-flow-step')].map(row => row.getBoundingClientRect()); return rows.every((row, i) => Math.abs(row.top - rows[0].top) < 1 && (!i || row.left > rows[i - 1].right)); })()"), "meeting stages flow left to right");
  assert.deepEqual(await evaluate("[...document.querySelectorAll('.meeting-flow-node h3')].map(node => node.textContent)"), ["逐字稿", "/meeting-notes", "/create-tasks", "/fetch-task"]);
  assert(await evaluate("document.querySelector('.meeting-sync-branch [data-demo-document=upload-meeting]') !== null"), "Notion knowledge sync remains accessible as a supporting branch");
  await scrollTo("welcome");
  await sleep(400);
  assert.equal(await evaluate("document.querySelectorAll('#claude-chat .chat-entry').length"), 0);
  // Reduced motion renders all content immediately and lets us cover every skill.
  await call("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: "reduce" }] });
  const names = await evaluate("[...document.querySelectorAll('.demo-scene')].map(e => e.dataset.scenePanel)");
  for (const name of names) {
    await scrollTo(name);
    await until("document.querySelector('#claude-chat').dataset.demo === " + JSON.stringify(name) + " && document.querySelector('#claude-chat .chat-complete').disabled");
    const expected = Number(await evaluate("document.querySelector('#demo-" + name + "').dataset.messageCount")) - Number(await evaluate("document.querySelectorAll('#claude-chat [data-role=question]').length"));
    assert.equal(await evaluate("document.querySelectorAll('#claude-chat .chat-entry').length"), expected, name);
    assert.equal(await evaluate("document.querySelector('.file.is-active').dataset.scene"), name);
  }
  await evaluate("document.querySelector('[data-scene=upload-meeting]').click()");
  await until("document.querySelector('#claude-chat .chat-complete').disabled");
  assert.equal(await evaluate("document.querySelector('#claude-chat').dataset.demo"), "meeting-notes");
  assert.deepEqual(await evaluate("[...document.querySelectorAll('#claude-chat [data-role=skill] code')].map(e => e.textContent)"), ["/meeting-notes", "/upload-meeting", "/create-tasks", "/fetch-task"]);
  assert.equal(await evaluate("document.querySelectorAll('.skill-related [data-demo-document]').length"), 5);
  assert(await evaluate("document.querySelector('[data-skill-entry=meeting-notes] [data-demo-document=meeting-transcript]') !== null"), "source preview sits under /meeting-notes");
  assert(await evaluate("['upload-meeting', 'create-tasks', 'fetch-task'].every(id => document.querySelector('[data-skill-entry=' + id + '] [data-demo-document=' + id + ']'))"), "each meeting output sits under its skill");
  await evaluate("document.querySelector('[data-scene=fetch-task]').click()");
  assert.equal(await evaluate("document.querySelector('#claude-chat').dataset.demo"), "meeting-notes", "fetch-task joins the information-to-work conversation");
  assert.equal(await evaluate("document.querySelectorAll('#demo-fetch-task').length"), 0, "no duplicate standalone fetch-task section");
  await evaluate("document.querySelector('.meeting-flow-work .stage-view').click()");
  assert.equal(await evaluate("document.querySelector('[role=tab][aria-selected=true]').id"), "tab-fetch-task", "local task preview opens the correct IDE tab");
  await evaluate("document.querySelector('.editor-tab-close').click()");
  await scrollTo("wrap-up");
  assert.equal(await evaluate("document.querySelectorAll('#claude-chat [data-role=divider]').length"), 2);
  await scrollTo("verify");
  const savedScroll = await evaluate("document.querySelector('#story-panel').scrollTop");
  await evaluate("document.querySelector('[data-method-play=code-review]').click()");
  await until("document.querySelector('#claude-chat .chat-complete').disabled");
  assert.equal(await evaluate("document.querySelector('#story-panel').scrollTop"), savedScroll, "stage CTA does not jump the reader back to the section top");
  assert(await evaluate("document.querySelector('[data-method-stage=code-review]').classList.contains('is-done')"), "diagram advances with its conversation");
  await sleep(500);
  assert(await evaluate("(() => { const rail = document.querySelector('#demo-verify .quality-rail'); const line = getComputedStyle(rail, '::after'); return parseFloat(line.getPropertyValue('--rail-done')) > 0 && Math.abs(parseFloat(line.getPropertyValue('--rail-done')) - parseFloat(rail.style.getPropertyValue('--rail-fill'))) < 2; })()"), "completed quality connector turns green through the finished stage");
  assert(await evaluate("(() => { const label = document.querySelector('#demo-verify [data-method-stage=code-review] .quality-label'); const style = getComputedStyle(label); return style.backgroundColor === getComputedStyle(document.querySelector('#demo-verify [data-method-stage=verify] .quality-label')).backgroundColor && style.color !== style.backgroundColor; })()"), "completed step keeps a dark tile with green text");
  const savedChat = await evaluate("document.querySelector('#claude-chat .chat-thread').innerText");
  const targetsBefore = (await call("Target.getTargets")).targetInfos.length;
  await evaluate("document.querySelector('#demo-verify [data-demo-document=code-review]').click()");
  assert.equal(await evaluate("document.querySelector('[role=tab][aria-selected=true]').id"), "tab-code-review");
  assert.equal(await evaluate("document.querySelector('#document-code-review pre').textContent"), await evaluate("window.DEV_SKILLS_DEMOS['code-review'].artifact"));
  assert(await evaluate("document.querySelector('#story-panel').hidden"));
  assert.equal(await evaluate("document.querySelector('#claude-chat .chat-thread').innerText"), savedChat);
  assert.equal((await call("Target.getTargets")).targetInfos.length, targetsBefore, "no browser tabs opened");
  await evaluate("document.querySelector('#document-code-review .document-return').click()");
  assert.equal(await evaluate("document.querySelector('#story-panel').scrollTop"), savedScroll);
  await scrollTo("sync");
  assert(await evaluate("document.querySelector('[data-skill-entry=code-review] [data-demo-document=code-review]') !== null"), "open document remains under its skill");
  assert(await evaluate("document.querySelector('[data-skill-entry=update-docs] [data-demo-document=update-docs]') === null"), "unrelated closed document disappears");
  await evaluate("document.querySelector('[data-skill-entry=code-review] [data-demo-document=code-review]').click()");
  await evaluate("document.querySelector('#document-code-review .document-return').click()");
  await scrollTo("verify");
  await evaluate("document.querySelector('#demo-verify [data-demo-document=code-review]').click()");
  assert.equal(await evaluate("document.querySelectorAll('[role=tab]').length"), 2, "reuse existing document tab");
  await evaluate("document.querySelector('#tab-code-review').dispatchEvent(new KeyboardEvent('keydown', {key:'Delete', bubbles:true}))");
  assert.equal(await evaluate("document.querySelectorAll('[role=tab]').length"), 1);
  await scrollTo("report");
  assert(await evaluate("document.querySelector('#demo-report .document-preview').getBoundingClientRect().left > document.querySelector('#demo-report .handoff-summary').getBoundingClientRect().right"), "report preview is beside the handoff summary");
  assert(await evaluate("document.querySelector('#demo-setup-notion .document-preview').getBoundingClientRect().left > document.querySelector('#demo-setup-notion .picture-hub').getBoundingClientRect().right"), "setup preview is beside its illustration");
  assert(await evaluate("document.querySelector('#demo-report .document-preview').getBoundingClientRect().height < 290"), "compact document preview");
  assert(await evaluate("getComputedStyle(document.querySelector('#demo-report .document-preview-excerpt'), '::after').backgroundImage.includes('linear-gradient')"), "gradient masks document bottom");
  assert(await evaluate("getComputedStyle(document.querySelector('#demo-report .document-preview-open')).position === 'absolute' && document.querySelector('#demo-report .document-preview-open').getBoundingClientRect().top < document.querySelector('#demo-report .document-preview-excerpt').getBoundingClientRect().bottom"), "button floats over gradient");
  await evaluate("document.querySelector('#demo-report .document-preview-open').click()");
  assert.equal(await evaluate("document.querySelector('[role=tab][aria-selected=true]').id"), "tab-report");
  await evaluate("document.querySelector('.editor-tab-close').click()");
  await evaluate("document.querySelector('.theme-toggle').click()");
  assert(await evaluate("document.body.classList.contains('light')"));
  await evaluate("document.querySelector('.theme-toggle').click()");
  for (const width of [1024, 901]) {
    await call("Emulation.setDeviceMetricsOverride", { width, height: 900, deviceScaleFactor: 1, mobile: false });
    await sleep(90);
    assert(await evaluate("document.documentElement.scrollWidth <= innerWidth"), "desktop width " + width);
  }
  await call("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
  await evaluate("window.scrollTo({top:0, behavior:'instant'})");
  await sleep(120);
  assert.equal(await evaluate("getComputedStyle(document.querySelector('#claude-chat')).display"), "none");
  assert(await evaluate("document.documentElement.scrollWidth <= innerWidth"), "mobile has no horizontal overflow");
  assert(await evaluate("[...document.querySelectorAll('.demo-scene .picture-node, .demo-scene .flow-node')].every(node => { const rect = node.getBoundingClientRect(); return Math.abs(rect.width - rect.height) < 1 && node.scrollHeight <= node.clientHeight + 1; })"), "mobile square nodes contain their labels");
  await evaluate("document.querySelector('#demo-meeting-notes').scrollIntoView({behavior:'instant'})");
  await until("document.querySelectorAll('#demo-meeting-notes .chat-entry').length === ['meeting-notes','upload-meeting','create-tasks','fetch-task'].reduce((n,id) => n + window.DEV_SKILLS_DEMOS[id].messages.length - window.DEV_SKILLS_DEMOS[id].messages.filter(message => message[0] === 'question').length, 0)");
  assert(await evaluate("document.querySelector('#demo-meeting-notes .inline-demo').getBoundingClientRect().height > 0"));
  assert(await evaluate("document.querySelector('#demo-meeting-notes .inline-demo .chat-compose') !== null"), "mobile conversation has its own composer");
  assert(await evaluate("document.querySelector('#demo-meeting-notes .chat-document-chip[data-demo-document=meeting-notes]') !== null"), "mobile chips render in combined conversation");
  assert(await evaluate("[...document.querySelectorAll('.chat-document-chip')].every(chip => chip.closest('.chat-bubble') && chip.closest('[data-role=assistant]'))"), "all file chips stay inside assistant replies");
  const mobilePosition = await evaluate("window.scrollY");
  await evaluate("document.querySelector('#demo-meeting-notes [data-demo-document]').click()");
  assert(await evaluate("document.documentElement.scrollWidth <= innerWidth"), "document mobile width");
  await evaluate("document.querySelector('#tab-story').click()");
  assert(Math.abs(await evaluate("window.scrollY") - mobilePosition) < 2, "mobile reading position retained");
  await evaluate("document.querySelector('#install').scrollIntoView({behavior:'instant'})");
  await evaluate("(() => { const picker = document.querySelector('#demo-install [data-host-picker]'); picker.value = 'claude'; picker.dispatchEvent(new Event('change')); })()");
  await evaluate("document.querySelector('#install [data-demo-replay=install]').click()");
  await evaluate("document.querySelector('#demo-install [data-inline-complete=install]').click()");
  await until("document.querySelector('#demo-install .chat-thread').textContent.includes('重啟 Claude Code')");
  await evaluate("(() => { const picker = document.querySelector('#demo-install [data-host-picker]'); picker.value = 'codex'; picker.dispatchEvent(new Event('change')); })()");
  await evaluate("document.querySelector('#demo-install [data-inline-complete=install]').click()");
  await until("document.querySelector('#demo-install .chat-thread').textContent.includes('git clone')");
  assert(await evaluate("document.querySelector('#demo-install .chat-thread').textContent.includes('沒有替你執行指令')"), "install demo switches to Codex without executing anything");
  assert(await evaluate("document.documentElement.scrollWidth <= innerWidth"), "installation stays within mobile width");
  assert.equal(errors.length, 0, JSON.stringify(errors));
  console.log("PASS: 16 skills in 8 method-led scenes; continuous workflows; host switch; scroll replay; contextual files; return buttons; IDE tabs; icons; typing; desktop/mobile; no JS errors.");
  // Screenshots last: capture can stall the CDP connection on some installations.
  if (process.argv.includes("--screenshots")) {
    await evaluate("document.querySelector('#demo-meeting-notes .inline-demo').scrollIntoView({behavior:'instant'})");
    let shot = await call("Page.captureScreenshot", { format: "png" });
    writeFileSync(path.join(shots, "mobile.png"), Buffer.from(shot.data, "base64"));
    await call("Emulation.setDeviceMetricsOverride", { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false });
    await sleep(200);
    for (const id of ["meeting-notes", "sync", "verify", "wrap-up", "report", "find-session", "improve"]) {
      await scrollTo(id);
      await sleep(400);
      shot = await call("Page.captureScreenshot", { format: "png" });
      writeFileSync(path.join(shots, id + "-dark.png"), Buffer.from(shot.data, "base64"));
    }
    await scrollTo("verify");
    shot = await call("Page.captureScreenshot", { format: "png" });
    writeFileSync(path.join(shots, "review-dark.png"), Buffer.from(shot.data, "base64"));
    await evaluate("document.querySelector('.theme-toggle').click()");
    for (const id of ["meeting-notes", "sync", "verify"]) {
      await scrollTo(id);
      shot = await call("Page.captureScreenshot", { format: "png" });
      writeFileSync(path.join(shots, id + "-light.png"), Buffer.from(shot.data, "base64"));
    }
    await scrollTo("welcome");
    await evaluate("document.querySelector('.editor__scroll').scrollTop += document.querySelector('.lifecycle-heading').getBoundingClientRect().top - document.querySelector('.editor__scroll').getBoundingClientRect().top");
    await sleep(120);
    shot = await call("Page.captureScreenshot", { format: "png" });
    writeFileSync(path.join(shots, "lifecycle-light.png"), Buffer.from(shot.data, "base64"));
    console.log("Screenshots: " + shots);
  }
} finally { clearTimeout(deadline); ws?.close(); chrome.kill(); }
