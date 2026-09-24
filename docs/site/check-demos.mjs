import assert from "node:assert/strict";
import { readdirSync, readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import vm from "node:vm";

const site = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(site, "../..");
const skills = readdirSync(path.join(repo, "skills")).filter(name => existsSync(path.join(repo, "skills", name, "SKILL.md"))).sort();
const excluded = ["prd", "spec", "spec-review", "headless-shots"];
const featured = skills.filter(id => !excluded.includes(id));
const files = readdirSync(path.join(site, "demos")).filter(name => name.endsWith(".js")).sort();
const context = vm.createContext({ window: {} });
for (const file of files) vm.runInContext(readFileSync(path.join(site, "demos", file), "utf8"), context, { filename: file, timeout: 500 });
const demos = context.window.DEV_SKILLS_DEMOS;
assert.deepEqual(Object.keys(demos).sort(), skills, "every repo skill must have one demo");
assert.deepEqual(files.map(name => name.replace(/\.js$/, "")).sort(), skills);
const html = readFileSync(path.join(site, "index.html"), "utf8");
const app = readFileSync(path.join(site, "app.js"), "utf8");
const visuals = readFileSync(path.join(site, "visuals.js"), "utf8");
const visualContext = vm.createContext({ window: {} });
vm.runInContext(visuals, visualContext);
const renderVisual = id => visualContext.window.devSkillsVisual({ id }, (target, label) => '<figure data-document="' + target + '">' + label + '</figure>');
assert.equal((renderVisual("sync").match(/class="flow-connector"/g) || []).length, 2, "sync restores the fetch/merge arrow connectors");
assert(!renderVisual("sync").includes("sync-branches"), "sync branch redesign is undone");
assert(renderVisual("verify").includes('data-visual-kind="test-fix-loop"'), "verify repeats tests and fixes rather than generating a checklist");
assert(renderVisual("verify").includes('不把未測當作通過'), "blocked checks stay explicit");
assert(!demos.verify.messages.some(message => message[2]?.documents), "verify does not claim to generate a document");
assert(demos.verify.messages.filter(([role, text]) => role === "tool" && text.includes("Edit")).length >= 2, "verify demonstrates repeated fixes before passing");
assert(demos["create-tasks"].artifact.includes("已核准並寫入 Notion"), "task creation includes the actual simulated write result, not only a preview");
assert(renderVisual("report").includes('data-visual-kind="paper-stack"'), "report has a paper-stack metaphor");
assert(renderVisual("setup-notion").includes('class="hub-relations"') && renderVisual("setup-notion").includes('hub-relation--handoff'), "setup shows linked project, meeting and task nodes");
const allowed = ["user", "assistant", "tool", "artifact", "skill", "question", "agent", "divider"];
const privateData = /sparktoy|poolgress|biokey|dropout|龍杰|佩芳|Joey|\/Users\/|app\.notion\.com|notion\.so\/[a-f0-9]|[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}/i;
for (const [id, d] of Object.entries(demos)) {
  assert.equal(d.id, id);
  if (featured.includes(id)) {
    const opening = d.messages.find(([role]) => role !== "divider");
    assert.equal(opening[0], "user", id + ": starts with a user invocation");
    assert(opening[1].startsWith("/" + id), id + ": user invokes the skill explicitly");
    assert(!/琢奧|ERP|庫存|預留|缺貨|商品列表|倉管|12 件/.test([d.title, d.intro, d.input, d.why].join(" ")), id + ": main-page descriptions stay general; examples belong in visuals, files and chat");
  }
  assert(d.messages.length >= 6, id + ": needs a full conversation");
  assert(d.messages.some(([role, text]) => role === "skill" && text.includes("/" + id)), id + ": explicit skill invocation");
  assert(d.messages.some(([role]) => role === "assistant"));
  assert(d.messages.some(([role]) => role === "tool" || role === "artifact"));
  assert(d.input && d.output && d.artifact && d.why && d.intro);
  assert.equal(d.steps.length, 3);
  assert(d.routes.length > 0 && d.routes.every(r => r === "notion" || r === "github"));
  for (const [i, [role, text, metadata]] of d.messages.entries()) {
    assert(allowed.includes(role), id + ": role");
    assert.equal(typeof text, "string");
    if (role === "question") assert.equal(d.messages[i + 1]?.[0], "user", id + ": answers must follow automatically");
    if (metadata?.documents) {
      assert.equal(role, "assistant", id + ": file chips belong to assistant replies");
      assert(Array.isArray(metadata.documents) && metadata.documents.length > 0);
      assert(metadata.documents.every(target => featured.includes(target)), id + ": chips link to featured documents");
    }
    if (metadata?.flow) {
      assert(["transcript", "meeting-notes", "upload-meeting", "create-tasks", "fetch-task"].includes(metadata.flow.stage));
      assert(["working", "preview", "done"].includes(metadata.flow.state));
    }
  }
  assert(!privateData.test(JSON.stringify(d)), id + ": real project information");
  assert(!/讀書會|報名|候補|主持人|參加者|名額/.test(JSON.stringify(d)), id + ": stale scenario");
  assert.equal(html.includes('src="demos/' + id + '.js"'), featured.includes(id), id + ": only featured demos are loaded");
}
assert(!/data-choice|chat-choice|data-conversation|\.skill[\s"'<>]/.test(html + app), "no old choice gates or fake .skill filenames");
assert(html.includes("lifecycle-main-path") && html.includes("github-branch-path") && html.includes("branch-back"));
assert(!/[①②③④⑤⑥⑦⑧]/.test(html + app), "no planning chapter numbers");
assert(!/chat-routes|data-route=/.test(html), "no Notion/GitHub split in chat");
assert.equal((html.match(/class="role-card"/g) || []).length, 6);
assert(!/阿慎|小理|阿約|小準|阿溯|小快|role-description|role-specialty/.test(html), "six review roles show concise responsibilities without names or biographies");
assert(html.indexOf('src="app.js"') > html.lastIndexOf('src="demos/'));
assert(!privateData.test(app));
const featuredDemos = Object.fromEntries([...html.matchAll(/src="demos\/([^"]+)\.js"/g)].map(([, id]) => [id, demos[id]]));
const sceneContext = vm.createContext({ window: { DEV_SKILLS_DEMOS: featuredDemos } });
const sceneSetup = app.slice(app.indexOf('  const demos ='), app.indexOf('  const $ ='));
vm.runInContext(sceneSetup + '\nglobalThis.result = { scenes, aliases: [sceneId("upload-meeting"), sceneId("create-tasks"), sceneId("fetch-task")] };', sceneContext);
const sceneResult = JSON.parse(JSON.stringify(sceneContext.result));
assert.equal(sceneResult.scenes.length, 8, "six method scenes plus setup and a separate memory architecture");
assert.deepEqual(sceneResult.aliases, ["meeting-notes", "meeting-notes", "meeting-notes"]);
const meeting = sceneResult.scenes.find(d => d.id === "meeting-notes");
assert.deepEqual(meeting.skillIds, ["meeting-notes", "upload-meeting", "create-tasks", "fetch-task"]);
assert.deepEqual(meeting.messages, JSON.parse(JSON.stringify(meeting.skillIds.flatMap(id => demos[id].messages))), "meeting conversation keeps all four demos in order");
const playback = (count, inFlight) => JSON.parse(vm.runInContext('JSON.stringify(meetingPlaybackState(' + count + ',' + JSON.stringify(inFlight || null) + '))', sceneContext));
assert(Object.values(playback(0).states).every(state => state === "waiting"), "replay clears all completed outcomes");
let lastDone = new Set();
for (let index = 0; index < meeting.messages.length; index++) {
  const flow = meeting.messages[index][2]?.flow;
  const state = playback(index + 1);
  if (flow) assert.equal(state.states[flow.stage], flow.state, "animation follows explicit completed message events");
  for (const id of lastDone) assert.equal(state.states[id], "done", "completed outcomes stay visible");
  lastDone = new Set(Object.keys(state.states).filter(id => state.states[id] === "done"));
}
const taskWrite = meeting.messages.findIndex(message => message[2]?.flow?.stage === "create-tasks" && message[2]?.flow?.state === "done");
assert.equal(playback(taskWrite).states["create-tasks"], "preview", "approval alone does not claim that tasks were written");
assert.equal(playback(taskWrite, {stage: "create-tasks", state: "done"}).states["create-tasks"], "preview", "completion cannot appear before the tool message finishes");
assert(Object.values(playback(meeting.messages.length).states).every(state => state === "done"), "complete control restores every diagram result");
assert.equal(playback(0, {stage: "upload-meeting", state: "working"}).current, "upload-meeting", "in-flight starts can highlight their stage");
assert(html.includes('id="demo-files"') && html.includes('class="chat-ready"'));
assert.equal((html.match(/data-toggle-panel="explorer"/g) || []).length, 2, "explorer can be collapsed from its pane and restored from the activity bar");
assert.equal((html.match(/data-toggle-panel="chat"/g) || []).length, 2, "chat can be collapsed from its header and restored from the titlebar");
assert(app.includes('function setPanel(name, visible)') && app.includes('button.setAttribute("aria-expanded", String(visible))'), "panel toggles expose their open state");
assert(html.includes('data-host-picker') && html.includes('foojiayin'));
assert(app.includes('class="section-cta document-return"'), "document return button");
assert(app.includes('class="section-cta document-return">← 返回</button>'), "return button keeps the arrow and short label");
assert(app.includes('else if (id !== active) play(id, true)'), "scroll-back replay");
assert(app.includes('data-assistant-name') && app.includes('class="skill-command"'), "assistant skill label and code typography");
assert(app.includes('const skillName = id => "/" + id'), "skill labels use slash notation");
assert(app.includes('node.classList.add("chat-skill-event", "chat-entry--tool")'), "skill calls share tool-event layout");
assert(app.includes('source: "Source", task: "Task", work: "Build", result: "Deliver"'), "English stepper labels");
assert(!html.includes('data-scene="wrap-up"'), "wrap-up has no pinned shortcut");
assert(!app.includes('members.filter(d => d.id !== "wrap-up")'), "wrap-up remains in the delivery explorer group");
assert.deepEqual(sceneResult.scenes.filter(d => d.chapter === "check").map(d => d.id), ["wrap-up", "verify"], "wrap-up precedes the connected quality method");
assert.deepEqual(sceneResult.scenes.filter(d => d.chapter === "handoff").map(d => d.id), ["report"], "one handoff process, not three isolated skill introductions");
assert.deepEqual(sceneResult.scenes.map(d => d.id), ["setup-notion", "meeting-notes", "sync", "wrap-up", "verify", "report", "find-session", "improve"], "memory architecture remains a separate page after handoff");
for (const id of ["sync", "verify", "report"]) {
  const scene = sceneResult.scenes.find(d => d.id === id);
  for (const skill of scene.skillIds) {
    assert.equal(scene.messages[scene.stageStarts[skill]][2].methodStage, scene.id === "report" && skill === "rename-session" ? "report" : skill, "stage seeks into its actual conversation and naming stays in the report step");
    assert(scene.messages.some(([role, text]) => role === "skill" && text.startsWith("/" + skill)), "grouped flow still demonstrates each skill");
  }
  if (id !== "sync") {
    assert.deepEqual(scene.messages.filter(([role, text]) => role === "user" && text.startsWith("/")).map(([, text]) => text), ["/wrap-up Full"], "Full wrap-up starts once; Claude invokes its child skills");
  }
}
const handoff = sceneResult.scenes.find(d => d.id === "report");
assert.equal(handoff.messages[handoff.stageStarts["rename-session"]][0], "skill", "after /report, /rename-session starts automatically without another user request");
assert(handoff.stageStarts.delivery < handoff.stageStarts["sync-report"] && handoff.stageStarts.resume > handoff.stageStarts["sync-report"]);
assert(handoff.messages.some(m => m[1].includes("部署還沒做")), "commit, PR and deployment stay distinct");
const methods = readFileSync(path.join(site, "methods.js"), "utf8");
vm.runInContext(methods, visualContext);
for (const id of ["sync", "verify", "report", "find-session", "improve"]) {
  const markup = visualContext.window.devSkillsMethod({id}, target => `<figure>${target}</figure>`);
  assert(markup.includes("data-method-play"), id + ": stages can trigger chat");
  assert(!/琢奧|ERP|庫存|預留/.test(markup), id + ": explanations remain general");
}
assert(methods.includes('method-memory') && methods.includes('handoff-rail') && methods.includes('learning-cycle'), "different methods have distinct compositions");
assert(!methods.includes('<span>重要決定</span>'), "rejected four-label handoff treatment is removed");
assert(methods.includes('handoff-summary__track') && ['完成範圍', '驗證證據', '接續事項'].every(label => methods.includes(label)), "handoff shows three scannable report outcomes");
const handoffMarkup = visualContext.window.devSkillsMethod({id:"report"}, target => `<figure>${target}</figure>`);
assert(handoffMarkup.includes('<b>cleanup + commit</b>'), "handoff version step identifies /wrap-up as cleanup plus commit");
assert.equal((handoffMarkup.match(/data-method-stage=/g) || []).length, 4, "report and automatic naming share one handoff step");
assert(handoffMarkup.includes('/report</code><span aria-hidden="true"> → </span><code class="skill-name">/rename-session'), "report heading includes the automatic naming follow-up");
assert(!handoffMarkup.includes('data-demo-document="rename-session"') && !handoffMarkup.includes('data-demo-document="wrap-up"'), "no fictional file CTA for naming or delivery");
assert(methods.includes('class="playback-cta"') && app.includes('確認品質') && app.includes('找回工作脈絡'), "playback invitations describe each section");
const renderer = vm.createContext({ demos: featuredDemos });
vm.runInContext('const byId = new Map(Object.entries(demos)); const esc = value => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll(\'"\', "&quot;");\n' + app.slice(app.indexOf('  const documentNames ='), app.indexOf('  const relatedDocuments =')) + app.slice(app.indexOf('  const documentIcon ='), app.indexOf('  function sectionActions')) + '\nglobalThis.previews = Object.keys(demos).map(id => documentPreview(id));', renderer);
for (const preview of renderer.previews) {
  assert(preview.includes('class="document-preview-excerpt"') && preview.includes('<pre>'), "preview shows document text");
  assert(preview.indexOf('class="document-preview-open"') > preview.indexOf('</pre>'), "button is below preview content");
  assert(!preview.includes('target="_blank"'), "preview opens internal tabs");
}
assert(app.includes('data-skill-folder="wrap-up"') && app.includes('skill-folder__children'), "wrap-up skill folder");
assert(app.includes('messageNode(message, false)') && app.includes('appendDocumentChips(node, metadata);'), "chips appear after typing");
assert(app.includes('class="meeting-flow-detail"') && app.includes('function renderMeetingProgress('), "meeting stages follow dialogue progress");
assert(!app.includes('class="meeting-fold"'), "horizontal meeting stages keep all workflow outputs visible");
assert(["meeting-notes", "create-tasks", "fetch-task", "upload-meeting"].every(id => app.includes('<h3><code class="skill-name">/' + id + '</code></h3>')), "skills are step headings, not file preview titles");
assert(app.includes('class="meeting-sync-branch"'), "Notion meeting upload is a supporting branch, not an equal primary stage");
assert(app.includes('data-play-stage=') && app.includes('meetingStarts[stage]'), "stage CTAs seek directly to the matching dialogue segment");
assert(!app.includes('meetingStepActions("transcript", "meeting-transcript"') && !app.includes('data-flow-status="transcript"'), "the transcript stays visible as input without a duplicate skill CTA or playback status");
assert(!app.includes('data-flow-status=') && !methods.includes('method-status'), "playback status labels do not occupy the workflow diagrams");
assert(app.includes('if (!["meeting-notes", "sync", "verify", "report", "find-session"].includes(d.id)) $(".scene__content", section).insertAdjacentHTML("beforeend", sectionActions(d));'), "multi-step flows do not repeat their step and document CTAs in footer rows");
vm.runInContext('globalThis.intakePreview = meetingPreview("meeting-notes", \'<div class="workflow-output method-notes">整理結果</div>\');', renderer);
assert(!renderer.intakePreview.includes('preview-file-tab') && renderer.intakePreview.includes('<b>會議記錄.md</b>') && !renderer.intakePreview.includes('skill-name'), "restored preview uses a file caption; skills remain step headings");
assert(renderer.intakePreview.includes('class="document-preview-excerpt"') && renderer.intakePreview.includes('class="workflow-output method-notes"'), "document card wraps the original method illustration");
assert(renderer.intakePreview.includes('data-demo-document="meeting-notes"') && !renderer.intakePreview.includes('target="_blank"'), "preview opens the matching internal IDE tab");
assert(!app.includes('previewStudies') && !app.includes('studyObserver'), "temporary A/C comparison is removed");
assert(renderer.previews.every(preview => preview.includes('class="preview-line-number" aria-hidden="true">0</span>') && preview.includes('>查看文件 <span')), "document previews have zero-based line numbers and consistent CTA labels");
assert(!app.includes('updateMeetingFocus'), "scroll position no longer drives animation timing");
const styles = readFileSync(path.join(site, "styles.css"), "utf8");
for (const selector of [".meeting-flow-node h3 .skill-name", ".meeting-sync-branch .skill-name"]) {
  const declaration = styles.slice(styles.indexOf(selector)).split("}")[0];
  assert(declaration.includes("color: var(--accent)"), "workflow skill labels stay orange without an active state: " + selector);
}
assert(!styles.includes(".is-current .meeting-transform .skill-name"), "skill label color does not depend on scroll focus");
assert(!app.includes('class="demo-input"') && !app.includes('class="demo-reason"'), "no redundant input/why blocks");
assert(app.includes('output.append(illustration)') && app.includes('output.className = "illustrated-output"'), "preview is embedded beside its illustration");
vm.runInContext('globalThis.document = { createElement() { return { setAttribute() {} }; } }; globalThis.$ = (selector, node) => node.querySelector(selector);\n' + app.slice(app.indexOf('  function appendDocumentChips'), app.indexOf('  function renderMessageText')) + '\nglobalThis.bubble = { children: [], append(child) { this.children.push(child); } }; globalThis.node = { dataset: { role: "assistant" }, querySelector(selector) { return selector === ".chat-bubble" ? bubble : bubble.children[0]; } }; appendDocumentChips(node, { documents: ["report"] }); appendDocumentChips(node, { documents: ["report"] });', renderer);
assert.equal(renderer.bubble.children.length, 1, "one chip group inside assistant bubble, without duplicates");
assert(renderer.bubble.children[0].innerHTML.includes('data-demo-document="report"'));
assert(!app.includes('class="demo-artifact"'), "document bodies are no longer inline");
assert(app.includes('data-demo-replay=') && app.includes('data-demo-document='), "section CTAs");
assert(!app.includes('target="_blank"'), "documents do not open browser tabs");
assert(app.includes('function openDocument') && html.includes('id="story-panel"'), "internal editor tabs");
assert(!/(?<!\$)\$\([^\n;]*\)\.forEach/.test(app), "collections use querySelectorAll");
assert(html.indexOf('src="demos/setup-notion.js"') < html.indexOf('src="demos/meeting-notes.js"'), "setup before meeting notes");
const documentHtml = readFileSync(path.join(site, "document.html"), "utf8");
const documentScript = readFileSync(path.join(site, "document.js"), "utf8");
for (const [id, d] of Object.entries({ ...demos, "meeting-transcript": demos["meeting-notes"].source })) {
  if (excluded.includes(id)) {
    assert(!documentHtml.includes('src="demos/' + id + '.js"'), id + ": excluded from document viewer");
    continue;
  }
  assert(documentHtml.includes('src="demos/' + (id === "meeting-transcript" ? "meeting-notes" : id) + '.js"'), id + ": available in document viewer");
  const elements = new Map();
  const element = selector => {
    if (!elements.has(selector)) elements.set(selector, { textContent: "", hidden: false, setAttribute() {}, addEventListener() {} });
    return elements.get(selector);
  };
  const doc = { querySelector: element, body: { classList: { toggle() {}, contains() { return false; } } } };
  vm.runInNewContext(documentScript, { window: { DEV_SKILLS_DEMOS: demos }, document: doc, location: { search: "?skill=" + id }, URLSearchParams });
  assert.equal(element("#document-content").textContent, d.artifact, id + ": correct related document");
}
console.log("PASS: " + skills.length + " skill/demo files; automatic answers; explicit skills; both paths; six roles; no stale choices or private project data.");
console.log("PASS: " + featured.length + " featured demos and document views; four excluded skills; section CTAs; internal tabs; setup-notion before meeting-notes.");
