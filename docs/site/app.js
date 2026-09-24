(() => {
  "use strict";
  const demos = Object.values(window.DEV_SKILLS_DEMOS || {});
  const byId = new Map(demos.map(d => [d.id, d]));
  const meetingSkills = ["meeting-notes", "upload-meeting", "create-tasks", "fetch-task"];
  const workflowGroups = {
    sync: { skills: ["sync", "discuss"], title: "接好進度再動手", intro: "先接上團隊最新的程式，再帶著任務背景比較做法。大家對『現在在哪裡、接下來怎麼走』有共識，就不用寫到一半才發現彼此想的不一樣。" },
    verify: { skills: ["verify", "update-docs", "code-review"], title: "把品質確認好", intro: "寫完不是句點。先把測試跑起來，失敗就修、修完再跑；接著讓文件跟上，再請不同角色一起看。找到的問題，要修好或清楚留下，才不會悄悄被帶到下一輪。" },
    report: { skills: ["report", "rename-session", "sync-report"], title: "今天收好，明天接得上", intro: "交接不只是一句『做完了』。把成果和未完成事項留下、把修改存成版本，再把進度帶回團隊。下次回來，自己或同事都能知道接下來要從哪裡開始。" }
  };
  const sceneId = id => meetingSkills.includes(id) ? "meeting-notes" : Object.keys(workflowGroups).find(key => workflowGroups[key].skills.includes(id)) || id;
  const deliveryMessages = [
    ["user", "/wrap-up 繼續整理這輪修改，先確認提交範圍。"],
    ["skill", "/wrap-up · 整理與交付"],
    ["tool", "Git · 檢查本輪 diff、暫存檔與其他視窗的修改"],
    ["assistant", "琢奧 ERP 這輪的程式和報告都對上了。有一個測試用暫存檔可以清掉；另一個視窗的修改不在這次提交範圍。"],
    ["question", "清理這個暫存檔，提交本輪修改後怎麼交付？\n開 PR｜直接 push｜先保留本地"],
    ["user", "清掉暫存檔，這輪開 PR。其他視窗不要動。"],
    ["tool", "Cleanup · 只清除已確認的暫存檔；Git · 提交本輪修改"],
    ["tool", "GitHub · 推送這輪版本，建立 PR，附上驗證和未完成事項"],
    ["assistant", "PR 已建立，部署還沒做。接著把報告和這個版本的連結帶回原任務。", { documents: ["report"] }]
  ];
  const resumeMessages = [
    ["user", "/find-session 庫存預留，上次還留了哪些事情？"],
    ["skill", "/find-session"],
    ["tool", "Search · 依主題找到『庫存預留與取消』的對話，對照報告與任務結果"],
    ["assistant", "找到了。預留和取消已完成，查詢改善延後、缺貨通知還待確認；PR 等待 review，部署尚未進行。可以先讀報告，需要當時的取捨再打開原對話。", { documents: ["report", "find-session", "sync-report"] }]
  ];
  const scenes = demos.filter(d => sceneId(d.id) === d.id).map(d => d.id !== "meeting-notes" ? d : ({
    ...d,
    skillIds: meetingSkills,
    title: "從一段討論，到可以動手的工作",
    intro: "會議聊完，說好的事很容易散掉。我們先保留逐字稿、整理會議記錄，把確認要做的事接成 Notion 任務，再將任務背景帶進本地工作檔。開始討論與實作時，就不用把來龍去脈重講一次；記錄也會同步到 Notion，方便團隊查找。",
    why: "從原始討論到本地工作，每一步都帶著前面的背景往下走。任務不只要建得出來，也要讓接手的人知道為什麼做、接下來怎麼做。",
    messages: meetingSkills.flatMap(id => byId.get(id).messages)
  })).map(d => {
    if (d.id === "improve") {
      const stageStarts = { friction: 0, cause: 2, choose: 3, apply: 8 };
      return { ...d, stageStarts, messages: d.messages.map(([role, text, meta], index) => [role, text, { ...meta, methodStage: Object.keys(stageStarts).filter(key => stageStarts[key] <= index).at(-1) }]) };
    }
    const group = workflowGroups[d.id];
    if (!group) return d;
    const automaticStep = ([role, text]) => role !== "user" || !/^\/(?:verify|update-docs|code-review|report|rename-session|sync-report|wrap-up|find-session)\b/.test(text);
    const segments = group.skills.flatMap(id => {
      if (d.id === "report" && id === "rename-session") return [[id, byId.get(id).messages.slice(1)]];
      return id === "sync-report"
        ? [["delivery", deliveryMessages], [id, byId.get(id).messages]] : [[id, byId.get(id).messages]];
    });
    if (d.id === "report") segments.push(["resume", resumeMessages]);
    const wrappedSegments = d.id === "sync" ? segments : segments.map(([stage, messages], index) => [stage, index === 0 ? [["user", "/wrap-up Full"], ["skill", "/wrap-up · Full"], ...messages.filter(automaticStep)] : messages.filter(automaticStep)]);
    return { ...d, ...group, skillIds: group.skills, stageStarts: Object.fromEntries(wrappedSegments.map(([id], index) => [id, wrappedSegments.slice(0, index).reduce((n, [, messages]) => n + messages.length, 0)])), messages: wrappedSegments.flatMap(([stage, messages]) => messages.map(([role, text, meta]) => [role, text, { ...meta, methodStage: d.id === "report" && stage === "rename-session" ? "report" : stage }])) };
  });
  const sceneById = new Map(scenes.map(d => [d.id, d]));
  const meetingStarts = {};
  let meetingOffset = 0;
  for (const id of meetingSkills) {
    meetingStarts[id] = meetingOffset;
    meetingOffset += byId.get(id).messages.length;
  }
  meetingStarts.transcript = 0;
  meetingStarts["meeting-notes"] = 3;
  function meetingPlaybackState(count, inFlight) {
    const states = Object.fromEntries(["transcript", ...meetingSkills].map(id => [id, "waiting"]));
    let current = "transcript";
    const apply = flow => {
      if (!flow || !Object.hasOwn(states, flow.stage)) return;
      states[flow.stage] = flow.state;
      // Reading the source completes while note preparation is already underway.
      if (flow.stage !== "transcript" || current === "transcript") current = flow.stage;
    };
    for (const message of sceneById.get("meeting-notes").messages.slice(0, count)) apply(message[2]?.flow);
    if (inFlight?.state === "working") apply(inFlight);
    return { states, current };
  }
  const $ = (s, root = document) => root.querySelector(s);
  const $$ = (s, root = document) => [...root.querySelectorAll(s)];
  const esc = value => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
  const skillName = id => "/" + id;
  const chapters = [
    ["intake", "把討論整理成接得住的工作", "需求可能來自一次會議、一段討論，或同事的一句提醒。把背景與決定留下來，再接成任務、帶進工作區，讓後面的實作有根據。旁邊的對話會用虛構情境示範，往下讀就會自動播放。"],
    ["prepare", "接上進度，再把事情想清楚", "有了任務背景，還要接上同事最新的程式，再一起討論做法。先把彼此的進度與想法對齊，動手時就比較不容易走岔。"],
    ["check", "收工前，把這一輪好好收起來", "先選適合今天的收尾方式，再把品質與交接一起顧好。"],
    ["handoff", "留下結果，讓下一個人接得上", "檢查過哪些地方、還有什麼沒完成，都值得留下來。接著把結果寫成報告、替對話取個好找的名字，再回填團隊的任務進度。"],
    ["remember", "隔天回來，不用全部重講", "昨天怎麼決定的？哪個視窗改了這個檔案？Notion 留團隊進度，報告留成果，對話紀錄留當時的討論。它們各有用途，不是互相取代。"],
    ["evolve", "下次，可以少提醒一次", "流程也可以一起變好。先找出這次卡在哪裡，再決定哪些值得留下成規則；不需要把每個小偏好變成所有人的要求。"]
  ];
  const modes = `<div class="wrap-modes">
    <article class="wrap-mode wrap-mode--quick">
      <header><span class="mode-number" aria-hidden="true">↗</span><div><h3>Quick <small>今天先到這裡</small></h3><p>先把進度存好，明天或換個人都能接著做。</p></div></header>
      <ol class="mode-steps">
        <li class="mode-step--skipped" aria-label="Quick 略過 verify"><s><code>/verify</code></s></li>
        <li class="mode-step--skipped" aria-label="Quick 不執行 update-docs 的文件修改"><s><code>/update-docs</code></s></li>
        <li class="mode-step--skipped" aria-label="Quick 略過 code-review"><s><code>/code-review</code></s></li>
        <li><code>/report → /rename-session</code><span>留下這輪的結果，也替對話取個找得到的名字。</span></li>
        <li><code>cleanup + commit</code><span>確認哪些修改是這一輪的，再存成版本。</span></li>
        <li><code>push</code><span>確認後送到遠端，讓隊友接得到。</span></li>
        <li><code>/sync-report</code><span>有設定 Notion 時，把結果帶回原任務。</span></li>
        <li class="mode-step--skipped" aria-label="Quick 略過手動部署與 improve"><s><code>deploy → /improve</code></s></li>
      </ol>
      <p class="mode-footnote">文件先提建議，不直接改；這輪不跑驗證、review 和 improve。部署狀態會交代清楚，不手動部署。</p>
    </article>
    <article class="wrap-mode wrap-mode--full">
      <header><span class="mode-number" aria-hidden="true">✓</span><div><h3>Full <small>準備把這一輪交付出去</small></h3><p>除了存好程式，也把檢查、文件和團隊進度一起顧到。</p></div></header>
      <ol class="mode-steps">
        <li><code>/verify</code><span>照計畫跑檢查，確認真的能用。</span></li>
        <li><code>/update-docs</code><span>找出需要跟著改的文件，確認後更新。</span></li>
        <li><code>/code-review</code><span>六個角色分頭看，有問題先處理或記下來。</span></li>
        <li><code>/report → /rename-session</code></li>
        <li><code>cleanup + commit</code></li>
        <li><code>/sync-report</code></li>
        <li><code>deploy → /improve</code><span>確認部署安排，再回看流程哪裡可以更順。</span></li>
      </ol>
      <p class="mode-footnote">有一步卡住就說清楚，需要你決定的地方，不會當作已經同意。</p>
    </article>
  </div>`;

  const documentNames = {
    "meeting-transcript": "2026-09-18-庫存預留與取消討論-transcript.txt",
    "meeting-notes": "2026-09-18-庫存預留與取消討論.md", "setup-notion": "AGENTS.md",
    "upload-meeting": "Notion 會議", "create-tasks": "_plan-2026-09-18-庫存預留與取消討論.md",
    "sync": "同步結果", "fetch-task": "庫存預留與取消-3f9a21.md", "discuss": "2026-09-21-庫存預留與取消.md",
    "verify": "測試執行示範",
    "update-docs": "文件更新預覽", "code-review": "REVIEW.md",
    "report": "2026-09-22-庫存預留與取消-3f9a21.md", "rename-session": "session.md",
    "wrap-up": "收尾清單.md", "sync-report": "Notion 任務結果", "find-session": "demo-0922.log.md",
    "improve": "改進提案"
  };
  // Cards, chips and sidebar show what kind of document it is; the IDE tab shows the example filename above.
  const documentLabels = {
    "meeting-transcript": "逐字稿.txt", "meeting-notes": "會議記錄.md",
    "create-tasks": "任務建立紀錄.md", "fetch-task": "task.md", "discuss": "plan.md",
    "report": "report.md", "find-session": "session.log.md"
  };
  const documentLabel = id => documentLabels[id] || documentNames[id];
  byId.set("meeting-transcript", byId.get("meeting-notes").source);
  const relatedDocuments = {
    "sync": ["fetch-task", "discuss"],
    "report": ["report", "sync-report", "find-session"],
    "meeting-notes": ["meeting-transcript", ...meetingSkills],
    "upload-meeting": ["upload-meeting", "meeting-notes"],
    "code-review": ["code-review", "discuss"],
    "verify": ["discuss", "update-docs", "code-review"],
    "wrap-up": [],
    "sync-report": ["sync-report", "report"],
    "improve": ["improve", "report"]
  };
  const documentIcon = id => documentNames[id].endsWith(".md") ? '<span class="md-icon" aria-hidden="true">M↓</span>' : '<span class="document-icon" aria-hidden="true">▤</span>';
  const markdownLines = text => globalThis.DevSkillsMarkdown ? globalThis.DevSkillsMarkdown.lines(text) : String(text).split("\n").map(esc);
  const sceneCalls = {
    "setup-notion": ["接上團隊資料", '<path d="M12 3v6m0 0-7 4m7-4 7 4M5 13v6m14-6v6M2 19h6m8 0h6"/>'],
    "meeting-notes": ["討論變成工作", '<path d="M3 5h9v7H3zM12 8h4m-4 10h9M16 8l-2-2m2 2-2 2M4 18h7"/>'],
    "sync": ["接好進度", '<path d="M3 5h6l4 7h8M3 19h6l4-7M17 8l4 4-4 4"/>'],
    "wrap-up": ["選擇收尾方式", '<path d="M12 3v7m0 0-7 6m7-6 7 6M2 16h6v5H2zm14 0h6v5h-6z"/>'],
    "verify": ["確認品質", '<path d="M20 8a8 8 0 1 0 1 7m-1-12v5h-5m-7 4 3 3 5-5"/>'],
    "report": ["交接這一輪", '<path d="M3 6h8v6H3zM13 12h8v6h-8zM11 9h4m-2-2 2 2-2 2"/>'],
    "find-session": ["找回工作脈絡", '<circle cx="10" cy="10" r="6"/><path d="m15 15 6 6M7 10h6"/>'],
    "improve": ["留下這次經驗", '<path d="M20 8a9 9 0 0 0-15-3L2 8m0-6v6h6m-4 8a9 9 0 0 0 15 3l3-3m0 6v-6h-6"/>']
  };
  function documentPreview(id, caption = "") {
    const d = byId.get(id);
    const excerpt = markdownLines(d.artifact).slice(0, 12).map((line, i) => '<span class="preview-code-line"><span class="preview-line-number" aria-hidden="true">' + i + '</span><span>' + (line || '&#8203;') + '</span></span>').join("");
    return '<figure class="document-preview" data-preview-document="' + id + '"><figcaption>' + documentIcon(id) + '<div><b>' + esc(documentLabel(id)) + '</b>' + (caption ? '<small>' + esc(caption) + '</small>' : '') + '</div></figcaption><div class="document-preview-excerpt"><pre>' + excerpt + '</pre></div><a class="document-preview-open" href="document.html?skill=' + id + '" data-demo-document="' + id + '" aria-label="在 IDE 分頁開啟 ' + esc(documentLabel(id)) + '">查看文件 <span aria-hidden="true">↗</span></a></figure>';
  }
  const previewRow = ids => '<div class="document-preview-row">' + ids.map(id => documentPreview(id)).join("") + '</div>';
  function meetingPreview(id, content) {
    return '<figure class="document-preview meeting-preview" data-preview-document="' + id + '"><figcaption>' + documentIcon(id) + '<div><b>' + esc(documentLabel(id)) + '</b></div></figcaption><div class="document-preview-excerpt">' + content + '</div><a class="document-preview-open stage-view" href="document.html?skill=' + id + '" data-demo-document="' + id + '" aria-label="在 IDE 分頁開啟 ' + esc(documentLabel(id)) + '">查看文件 <span aria-hidden="true">↗</span></a></figure>';
  }
  function meetingStepActions(stage, documentId, title, card = false) {
    const skill = stage;
    return '<div class="meeting-step-actions">' + (card ? '' : '<a class="stage-view" href="document.html?skill=' + documentId + '" data-demo-document="' + documentId + '" aria-label="查看' + title + '的示範內容">查看文件 ↗</a>') + '<button type="button" class="stage-play playback-cta" data-play-stage="' + stage + '" aria-label="試試 /' + skill + '：' + title + '"><span>試試</span> <code class="cta-skill">/' + skill + '</code></button></div>';
  }
  function sectionActions(d) {
    const links = (relatedDocuments[d.id] || [d.id]).map(id =>
      '<a class="section-cta section-cta--document" href="document.html?skill=' + id + '" data-demo-document="' + id + '" aria-label="在編輯器開啟 ' + esc(documentLabel(id)) + '">' + documentIcon(id) + esc(documentLabel(id)) + ' <span aria-hidden="true">↗</span></a>'
    ).join("");
    const [call, drawing] = sceneCalls[d.id];
    return '<div class="section-actions" aria-label="' + d.id + ' 示範操作"><button type="button" class="section-cta section-cta--replay playback-cta playback-cta--' + d.id + '" data-demo-replay="' + d.id + '" aria-label="從頭重播 /' + d.id + ' 對話：' + call + '"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + drawing + '</svg><code class="cta-skill">/' + d.id + '</code><span>' + call + '</span></button>' + links + '</div>';
  }

  const folders = { intake: "Source", prepare: "Prepare", check: "Check", handoff: "Handoff", remember: "Memory", evolve: "Improve" };
  const wrapSkills = ["verify", "update-docs", "code-review", "report", "rename-session", "sync-report", "improve"];
  function explorerEntry(d, parent = false) {
    return '<div class="skill-entry" data-skill-entry="' + d.id + '"><a class="file file--nested' + (parent ? ' file--skill-folder' : '') + '" href="#demo-' + d.id + '" data-scene="' + d.id + '" title="demo 檔：demos/' + d.id + '.js">' + (parent ? '<span class="skill-folder-caret" aria-hidden="true">⌄</span>' : '') + '<span class="file__icon file__icon--skill" aria-hidden="true">✦</span><span>' + skillName(d.id) + '</span></a><div class="skill-related" data-skill-related="' + d.id + '" hidden></div></div>';
  }
  for (const [id, title, intro] of chapters) {
    const members = demos.filter(d => d.chapter === id);
    const explorerMembers = members.filter(d => !wrapSkills.includes(d.id));
    if (explorerMembers.length) $("#demo-files").insertAdjacentHTML("beforeend", '<div class="folder"><span>⌄</span>' + folders[id] + '</div>' + explorerMembers.map(d => d.id === "wrap-up" ? '<div class="skill-folder" data-skill-folder="wrap-up">' + explorerEntry(d, true) + '<div class="skill-folder__children" role="group" aria-label="wrap-up 收尾流程">' + wrapSkills.map(id => explorerEntry(byId.get(id))).join("") + '</div></div>' : explorerEntry(d)).join(""));
    const chapter = document.createElement("section");
    chapter.className = "demo-chapter";
    chapter.id = "chapter-" + id;
    chapter.setAttribute("aria-labelledby", "title-" + id);
    chapter.setAttribute("aria-label", title);
    chapter.removeAttribute("aria-labelledby");
    for (const d of scenes.filter(d => d.chapter === id)) {
      const section = document.createElement("section");
      section.className = "scene demo-scene";
      section.id = "demo-" + d.id;
      section.dataset.scenePanel = d.id;
      section.dataset.messageCount = d.messages.length;
      section.dataset.skills = (d.skillIds || [d.id]).join(",");
      section.setAttribute("aria-labelledby", "title-" + d.id);
      const routes = d.routes.map(r => '<span class="route-label route-label--' + r + '">' + (r === "notion" ? "N · Notion" : "⑂ · GitHub") + "</span>").join("");
      section.innerHTML = '<div class="scene__content"><div class="demo-eyebrow"><span class="skill-name">' + skillName(d.id) + "</span><div>" + routes + '</div></div><h2 id="title-' + d.id + '">' + esc(d.title) + '</h2><p class="scene__intro">' + esc(d.intro) + '</p>' + '<ol class="demo-steps">' + d.steps.map((s, i) => "<li><span>0" + (i + 1) + "</span>" + esc(s) + "</li>").join("") + '</ol>' + (d.id === "wrap-up" ? modes : "") + (d.id === "code-review" ? '<div class="review-people"></div>' : "") + '<div class="inline-demo" aria-label="' + d.id + ' 自動示範"><div class="inline-title"><b class="chat-host-name">Claude Code</b><label class="host-picker"><span class="sr-only">切換對話示範工具</span><select data-host-picker><option value="claude">Claude Code</option><option value="codex">Codex</option></select></label></div><div class="chat-thread" role="log" aria-label="示範對話" aria-live="off"></div><div class="inline-controls"><button type="button" data-inline-pause="' + d.id + '">暫停</button><button type="button" data-inline-complete="' + d.id + '">立即顯示完整對話</button><button type="button" data-inline-replay="' + d.id + '">重播</button></div><small>虛構情境 · 使用者輸入與確認皆為自動演示</small></div></div>';
      if (!["meeting-notes", "sync", "verify", "report", "find-session"].includes(d.id)) $(".scene__content", section).insertAdjacentHTML("beforeend", sectionActions(d));
      const steps = $(".demo-steps", section);
      if (d.id === "meeting-notes") {
        const eyebrow = $(".skill-name", section);
        eyebrow.className = "workflow-name";
        eyebrow.textContent = "把討論接成工作";
        steps.outerHTML = `<div class="skill-visual meeting-workflow">
          <ol class="meeting-flow" aria-label="逐字稿，整理成會議記錄，建立 Notion 任務，再帶進本地工作檔">
            <li class="meeting-flow-step meeting-flow-source is-current" data-meeting-step="transcript">
              <div class="meeting-flow-node"><span class="meeting-node-icon" aria-hidden="true"></span><h3>逐字稿</h3><small class="meeting-transform">保留大家原本說的話</small></div>
              <div class="meeting-flow-detail"><p class="meeting-description">討論可以很零散。先保留原文，之後才有地方回頭確認，不用靠記憶補空白。</p></div>
              ${meetingPreview("meeting-transcript", '<div class="meeting-source workflow-output"><p>「庫存只有 12 件。」</p><p>「取消後要還回去。」</p><p>「缺貨通知下次再聊。」</p></div>')}
            </li>
            <li class="meeting-flow-step meeting-flow-notes" data-meeting-step="meeting-notes">
              <div class="meeting-flow-node"><span class="meeting-node-icon" aria-hidden="true"></span><h3><code class="skill-name">/meeting-notes</code></h3><small class="meeting-transform">會議記錄 · 整理出決定與下一步</small></div>
              <div class="meeting-flow-detail"><p class="meeting-description">分清楚已決定、待確認和下一步。整理過的內容好讀，原文也不會被摘要取代。</p></div>
              ${meetingPreview("meeting-notes", '<div class="workflow-output method-notes"><dl><dt>已決定</dt><dd>預留與取消</dd><dt>待確認</dt><dd>缺貨通知</dd><dt>下一步</dt><dd>先完成已確認的部分</dd></dl></div>')}
              ${meetingStepActions("meeting-notes", "meeting-notes", "整理會議記錄", true)}
            </li>
            <li class="meeting-flow-step meeting-flow-tasks" data-meeting-step="create-tasks">
              <div class="meeting-flow-node"><span class="meeting-node-icon" aria-hidden="true"></span><h3><code class="skill-name">/create-tasks</code></h3><small class="meeting-transform">Notion 任務 · 確認後建立或連結</small></div>
              <div class="meeting-flow-detail"><p class="meeting-description">先比對現有工作、確認要做的事，再新建或連回既有任務，帶著會議背景往下做。</p></div>
              ${meetingPreview("create-tasks", '<div class="workflow-output method-tasks"><small data-task-write-status>候選任務 · 尚未寫入</small><div><span data-task-new-status>待新建</span><b>庫存預留與取消</b></div><div><span data-task-link-status>待連結</span><b>員工登入</b></div><p>缺貨通知還沒決定，先不建立。</p></div>')}
              ${meetingStepActions("create-tasks", "create-tasks", "建立 Notion 任務", true)}
            </li>
            <li class="meeting-flow-step meeting-flow-work" data-meeting-step="fetch-task">
              <div class="meeting-flow-node"><span class="meeting-node-icon" aria-hidden="true"></span><h3><code class="skill-name">/fetch-task</code></h3><small class="meeting-transform">本地工作檔 · 帶著背景開始做</small></div>
              <div class="meeting-flow-detail"><p class="meeting-description">把任務背景與決定帶回工作區，接著討論和實作。之後更新背景，也不會蓋掉自己的計畫與筆記。</p></div>
              ${meetingPreview("fetch-task", '<div class="workflow-output method-workspace"><div><span>任務背景</span><small>從 Notion 帶入 ↻</small></div><div><span>自己的計畫</span><small>保留，不覆寫</small></div><div><span>工作筆記</span><small>保留，不覆寫</small></div></div>')}
              ${meetingStepActions("fetch-task", "fetch-task", "帶進本地工作檔", true)}
            </li>
          </ol>
          <aside class="meeting-sync-branch" data-meeting-step="upload-meeting" aria-label="會議記錄的知識同步支線"><span aria-hidden="true">↳</span><div><h3><code class="skill-name">/upload-meeting</code></h3><b>也把記錄同步到 Notion</b><p>讓團隊找得到決定的來龍去脈。</p><p class="workflow-output meeting-sync-result">✓ 會議頁已建立，原文與記錄都已同步</p>${meetingStepActions("upload-meeting", "upload-meeting", "同步會議到 Notion")}</div></aside>
        </div>`;
      } else if (d.id === "wrap-up") {
        $("h2", section).textContent = "選擇收尾方式";
        steps.remove();
      } else if (window.devSkillsMethod(d, documentPreview)) {
        steps.outerHTML = window.devSkillsMethod(d, documentPreview);
        $(".demo-eyebrow", section).remove();
      } else steps.outerHTML = window.devSkillsVisual(d, documentPreview);
      if (d.id === "find-session") $("h2", section).textContent = "Memory：脈絡分別留在哪裡？";
      if (d.id === "improve") $("h2", section).textContent = "讓下次少踩一次坑";
      if (d.id === "verify") $(".method-review-team", section).append($("#review-team-template").content.cloneNode(true));
      if (d.id === "code-review") $(".review-people", section).append($("#review-team-template").content.cloneNode(true));
      const previewLocations = {
        "setup-notion": [".picture-hub", ["setup-notion"]],
        "discuss": [".decision-picture", ["discuss"]],
        "code-review": [".review-people", ["code-review"]],
      };
      if (previewLocations[d.id]) {
        const [selector, ids] = previewLocations[d.id];
        const illustration = $(selector, section);
        const output = document.createElement("div");
        output.className = "illustrated-output";
        illustration.replaceWith(output);
        output.append(illustration);
        output.insertAdjacentHTML("beforeend", previewRow(ids));
      }
      chapter.append(section);
    }
    $("#demo-chapters").append(chapter);
  }
  $("#demo-chapters").insertAdjacentHTML("beforeend", '<section class="chapter-heading ending"><div class="section-kicker">把兩條路接回來</div><h2>工作有留下，下一個人就接得到。</h2><p>Notion 留下需求、決定和工作結果；GitHub 留下程式修改與交付紀錄。哪些已完成、哪些還要驗收、哪些尚未部署，都分開交代。把「做到哪裡」說清楚，就是交接的一部分。</p><p>這裡介紹的 16 個 skill 都可以單獨使用，也能在需要時串起來。不必一次記住全部，從今天遇到的那件事開始就好。</p><a class="text-action" href="https://github.com/FooJiaYin/dev-skills#readme">安裝與完整使用說明 ↗</a></section>');

  const phaseIcons = {
    source: '<path d="M4 4h16v12H9l-5 4z"/><path d="M8 8h8M8 12h5"/>',
    task: '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 3h6v4H9zM9 12h6M9 16h4"/>',
    work: '<path d="m8 6-6 6 6 6m8-12 6 6-6 6m-3-15-2 18"/>',
    result: '<circle cx="12" cy="12" r="9"/><path d="m7 12 3 3 7-7"/>'
  };
  for (const [phase, drawing] of Object.entries(phaseIcons)) {
    const svg = '<svg viewBox="0 0 24 24" aria-hidden="true">' + drawing + '</svg>';
    const node = $(".lifecycle-node--" + ({source:"source",task:"notion",work:"work",result:"result"}[phase]) + " > i");
    node.innerHTML = svg;
    node.setAttribute("aria-hidden", "true");
  }
  const desktop = $("#claude-chat");
  const desktopThread = $(".chat-thread", desktop);
  const mobile = matchMedia("(max-width: 900px)");
  const reduced = matchMedia("(prefers-reduced-motion: reduce)");
  const progress = new Map();
  const follow = new WeakMap();
  let active = null, token = 0, paused = false, frame = 0, changingLayout = false;
  let editorTab = "story", storyWindowTop = 0, storyScrollTop = 0;
  let host = "claude";
  const hostName = () => host === "claude" ? "Claude Code" : "Codex";
  const openedDocuments = new Map();
  function updateRelatedFiles() {
    const ids = new Set([...(active ? relatedDocuments[active] || [active] : []), ...openedDocuments.keys()]);
    $$("[data-skill-related]").forEach(container => { container.innerHTML = ""; container.hidden = true; });
    for (const id of ids) {
      const owner = id === "meeting-transcript" ? "meeting-notes" : id;
      const container = $('[data-skill-related="' + owner + '"]');
      if (!container) continue;
      container.hidden = false;
      container.insertAdjacentHTML("beforeend", '<a class="file file--document' + (editorTab === id ? ' is-active' : '') + '" href="document.html?skill=' + id + '" data-demo-document="' + id + '" title="' + esc(documentLabel(id)) + '"' + (editorTab === id ? ' aria-current="page"' : '') + '>' + documentIcon(id) + '<span>' + esc(documentLabel(id)) + '</span>' + (openedDocuments.has(id) ? '<small title="已開啟分頁">●</small>' : '') + '</a>');
    }
  }
  function selectEditorTab(id, focus = true) {
    if (editorTab === "story" && id !== "story") {
      storyWindowTop = window.scrollY;
      storyScrollTop = $("#story-panel").scrollTop;
    }
    const returning = editorTab !== "story" && id === "story";
    editorTab = id;
    $("#story-panel").hidden = id !== "story";
    $(".editor-documents").hidden = id === "story";
    for (const [key, entry] of openedDocuments) entry.panel.hidden = key !== id;
    $$("[data-editor-tab]").forEach(tab => {
      const selected = tab.dataset.editorTab === id;
      tab.setAttribute("aria-selected", String(selected));
      tab.tabIndex = selected ? 0 : -1;
      if (selected) {
        if (focus) tab.focus({ preventScroll: true });
        const bar = $(".document-bar"), a = tab.getBoundingClientRect(), b = bar.getBoundingClientRect();
        if (a.left < b.left || a.right > b.right) bar.scrollLeft += a.left - b.left;
      }
    });
    if (returning) {
      $("#story-panel").scrollTop = storyScrollTop;
      if (mobile.matches) window.scrollTo({ top: storyWindowTop, behavior: "instant" });
    } else if (mobile.matches && id !== "story") window.scrollTo({ top: 0, behavior: "instant" });
    updateRelatedFiles();
  }
  function closeDocument(id) {
    const entry = openedDocuments.get(id);
    if (!entry) return;
    if (editorTab === id) selectEditorTab("story");
    entry.tab.remove();
    entry.panel.remove();
    openedDocuments.delete(id);
    updateRelatedFiles();
  }
  function openDocument(id) {
    const d = byId.get(id);
    if (!d) return;
    if (!openedDocuments.has(id)) {
      const tab = document.createElement("div");
      tab.className = "editor-tab-item";
      tab.innerHTML = '<button type="button" class="editor-tab" role="tab" id="tab-' + id + '" aria-controls="document-' + id + '" aria-selected="false" data-editor-tab="' + id + '">' + documentIcon(id) + esc(documentNames[id]) + '</button><button type="button" class="editor-tab-close" aria-label="關閉 ' + esc(documentNames[id]) + '">×</button>';
      $(".document-bar").append(tab);
      $(".editor-tab-close", tab).addEventListener("click", () => closeDocument(id));
      const panel = document.createElement("section");
      panel.className = "editor-document";
      panel.id = "document-" + id;
      panel.setAttribute("role", "tabpanel");
      panel.setAttribute("aria-labelledby", "tab-" + id);
      panel.tabIndex = 0;
      panel.innerHTML = '<div class="document-sheet"><p class="editor-document-path"></p><h1></h1><p class="document-disclaimer">琢奧 ERP · 虛構示範文件，方便你看看這個階段會留下什麼。</p><pre class="editor-document-content"></pre><button type="button" class="section-cta document-return">← 返回</button></div>';
      $(".document-return", panel).addEventListener("click", () => selectEditorTab("story"));
      $("h1", panel).textContent = documentNames[id];
      $(".editor-document-path", panel).textContent = d.output;
      $("pre", panel).innerHTML = markdownLines(d.artifact).join("\n");
      $(".editor-documents").append(panel);
      openedDocuments.set(id, { tab, panel });
    }
    selectEditorTab(id);
    if (!mobile.matches) {
      setPanel("explorer", true);
      $('.skill-related .file--document[data-demo-document="' + id + '"]')?.scrollIntoView({ block: "nearest" });
    }
  }
  $(".document-bar").addEventListener("click", event => {
    const tab = event.target.closest("[data-editor-tab]");
    if (tab) selectEditorTab(tab.dataset.editorTab);
  });
  $(".document-bar").addEventListener("keydown", event => {
    const tab = event.target.closest("[data-editor-tab]");
    if (!tab) return;
    const tabs = $$("[data-editor-tab]"), index = tabs.indexOf(tab);
    const next = { ArrowRight: (index + 1) % tabs.length, ArrowLeft: (index - 1 + tabs.length) % tabs.length, Home: 0, End: tabs.length - 1 }[event.key];
    if (next !== undefined) { event.preventDefault(); selectEditorTab(tabs[next].dataset.editorTab); }
    if (event.key === "Delete" && editorTab !== "story") { event.preventDefault(); closeDocument(editorTab); }
  });
  selectEditorTab("story", false);
  const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
  const threadFor = id => mobile.matches ? $("#demo-" + id + " .chat-thread") : desktopThread;
  $$(".chat-thread").forEach(thread => {
    follow.set(thread, true);
    thread.addEventListener("scroll", () => follow.set(thread, thread.scrollHeight - thread.clientHeight - thread.scrollTop < 50), { passive: true });
  });
  function scrollChat(thread) { if (follow.get(thread)) thread.scrollTop = thread.scrollHeight; }
  const labels = { user: "你 · 示範", assistant: "Claude", skill: "Skill", tool: "工具活動 · 示意", artifact: "檔案與結果 · 示意", question: "確認問題 · 回答會自動接續", agent: "Reviewer", divider: "兩種收尾情境，依序自動示範" };
  const selectedAnswers = {
    "沿用上層設定？": "沿用", "這兩項可以寫入嗎？": "核准", "參與者": "先留空",
    "這兩項怎麼處理？": "只修選定項目", "確認提交後，要推到 GitHub 嗎？": "先不 push",
    "報告和這次修改的提交範圍確認好了。怎麼交付？": "開 PR", "目前沒有自動部署設定，要現在部署嗎？": "先不要",
    "驗證報告的寫法要用在哪裡？": "團隊共用", "這張任務要更新成哪個狀態？": "Testing（測試中）", "GitHub Link 目前是空白，要補上這輪版本嗎？": "補上這輪版本",
    "套用這兩項更新嗎？": "全部套用", "清理這個暫存檔，提交本輪修改後怎麼交付？": "開 PR"
  };
  function renderQuestion(body, text) {
    const [prompt, options = ""] = text.split("\n");
    body.innerHTML = '<p class="question-prompt">' + esc(prompt) + '</p><div class="question-options" role="group" aria-label="示範選項">' + options.split("｜").filter(Boolean).map(option => '<button type="button" class="question-option" disabled aria-label="' + esc(option) + '，示範選項">' + esc(option) + '</button>').join("") + '</div>';
  }
  function markQuestionAnswer(node, text) {
    const chosen = selectedAnswers[text.split("\n")[0]];
    for (const option of $$(".question-option", node)) {
      const selected = option.textContent === chosen;
      option.classList.toggle("is-selected", selected);
      if (selected) option.setAttribute("aria-label", chosen + "，示範已選");
    }
  }
  function messageNode([role, text, metadata], showDocuments = true) {
    const node = document.createElement("div");
    node.className = "chat-entry chat-entry--" + role;
    node.dataset.role = role;
    if (role === "user" || role === "assistant") {
      node.classList.add("chat-message", "chat-message--" + role);
      node.innerHTML = '<div class="chat-message__role"><i>' + (role === "user" ? "你" : "✦") + '</i><span' + (role === "assistant" ? ' data-assistant-name' : '') + '>' + (role === "assistant" ? hostName() : labels[role]) + '</span></div><div class="chat-bubble"></div>';
    } else {
      if (role === "skill") node.classList.add("chat-skill-event", "chat-entry--tool");
      node.innerHTML = '<span class="event-label">' + (role === "skill" ? '<span data-assistant-name>' + hostName() + '</span> · Skill' : labels[role]) + '</span><div class="event-body"></div>';
    }
    const body = $(".chat-bubble, .event-body", node);
    if (role === "question") renderQuestion(body, text);
    else renderMessageText(body, text);
    if (showDocuments) appendDocumentChips(node, metadata);
    return node;
  }
  function appendDocumentChips(node, metadata) {
    const bubble = $(".chat-bubble", node);
    if (node.dataset.role !== "assistant" || !bubble) return;
    const ids = [...new Set(metadata?.documents || [])].filter(id => byId.has(id) && documentNames[id]);
    if (!ids.length || $(".chat-documents", node)) return;
    const group = document.createElement("div");
    group.className = "chat-documents";
    group.setAttribute("aria-label", "相關示範文件");
    group.innerHTML = ids.map(id => '<a class="chat-document-chip" href="document.html?skill=' + id + '" data-demo-document="' + id + '" aria-label="在 IDE 分頁開啟 ' + esc(documentLabel(id)) + '">' + documentIcon(id) + '<span>' + esc(documentLabel(id)) + '</span><span aria-hidden="true">↗</span></a>').join("");
    bubble.append(group);
  }
  function renderMessageText(body, text) {
    body.innerHTML = esc(text).replace(/(^|[\s（(「])\/[a-z][a-z0-9-]*(?::[a-z][a-z0-9-]*)?/g, match => {
      const slash = match.indexOf("/");
      return match.slice(0, slash) + '<code class="skill-command">' + match.slice(slash) + '</code>';
    });
  }
  function setHost(value) {
    host = value === "codex" ? "codex" : "claude";
    $$("[data-host-picker]").forEach(picker => { picker.value = host; });
    $$(".chat-host-name, [data-assistant-name]").forEach(label => { label.textContent = hostName(); });
    desktop.setAttribute("aria-label", hostName() + " 對話示意");
    const shortcut = $('[data-jump="chat"]');
    shortcut.setAttribute("aria-label", hostName() + " 對話");
    shortcut.title = hostName() + " 對話";
  }
  $$("[data-host-picker]").forEach(picker => picker.addEventListener("change", () => setHost(picker.value)));
  function restore(thread, d, count) {
    thread.replaceChildren(...d.messages.slice(0, count).map((message, index) => {
      const node = messageNode(message);
      if (message[0] === "question" && index + 1 < count) markQuestionAnswer(node, message[1]);
      return node;
    }));
    follow.set(thread, true);
    scrollChat(thread);
    if (d.id === "meeting-notes") renderMeetingProgress(count);
    renderMethodProgress(d, count);
    syncPlaybackButtons(d.id, count === d.messages.length);
    showStatusSkill(d, count);
  }
  function controls(done = false) {
    $(".chat-pause").textContent = paused ? "繼續" : "暫停";
    $(".chat-pause").disabled = !active || done;
    $(".chat-complete").disabled = !active || done;
    $(".chat-reset").disabled = !active;
    $$("[data-inline-pause]").forEach(button => {
      const current = button.dataset.inlinePause === active;
      button.textContent = current && paused ? "繼續" : "暫停";
      button.disabled = !current || done;
    });
  }
  function mark(id) {
    updateRelatedFiles();
    $$(".file[data-scene]").forEach(file => {
      const selected = file.dataset.scene === id;
      file.classList.toggle("is-active", selected);
      if (selected) file.setAttribute("aria-current", "location");
      else file.removeAttribute("aria-current");
    });
    const selected = $('.file[data-scene="' + id + '"]');
    if (selected && !mobile.matches) {
      const nav = $(".file-tree"), a = selected.getBoundingClientRect(), b = nav.getBoundingClientRect();
      if (a.top < b.top || a.bottom > b.bottom) nav.scrollTop += a.top - b.top - nav.clientHeight / 2;
    }
  }
  function clear() {
    token++;
    active = null;
    paused = false;
    desktopThread.replaceChildren();
    desktop.classList.add("is-reading");
    $$(".playback-cta").forEach(button => button.classList.remove("is-playing", "is-complete"));
    delete desktop.dataset.demo;
    $("#chat-skill").textContent = "";
    $(".chat-compose div").textContent = "使用者輸入也會自動演出";
    $("#demo-progress").textContent = "README.md";
    $("#status-skill").hidden = true;
    $("#status-page").hidden = true;
    $$("[data-stage]", desktop).forEach(stage => stage.classList.remove("is-active"));
    mark("welcome");
    controls();
  }
  async function ready(t) {
    while (paused && t === token) await wait(60);
    return t === token;
  }
  async function play(id, replay = false) {
    id = sceneId(id);
    const d = sceneById.get(id);
    if (!d) return;
    const t = ++token;
    active = id;
    paused = false;
    if (replay) progress.set(id, 0);
    const count = progress.get(id) || 0, thread = threadFor(id);
    desktop.classList.remove("is-reading");
    desktop.dataset.demo = id;
    $("#chat-skill").textContent = d.skillIds ? d.title : skillName(id);
    $("#demo-progress").textContent = $("#demo-" + id + " h2")?.textContent || d.title;
    $("#status-page").textContent = (scenes.indexOf(d) + 1) + " / " + scenes.length;
    $("#status-page").hidden = false;
    $(".chat-compose div").textContent = "使用者輸入也會自動演出";
    $$("[data-stage]", desktop).forEach(item => item.classList.toggle("is-active", item.dataset.stage === d.chapter));
    mark(id);
    restore(thread, d, count);
    controls(count === d.messages.length);
    for (let i = count; i < d.messages.length; i++) {
      if (!await ready(t)) return;
      const message = d.messages[i], [role, text, metadata] = message, node = messageNode(message, false);
      const body = $(".chat-bubble, .event-body", node);
      const typed = !reduced.matches && (role === "assistant" || role === "user");
      if (typed) body.textContent = "";
      thread.append(node);
      showStatusSkill(d, i + 1);
      if (id === "meeting-notes") renderMeetingProgress(i, metadata?.flow);
      renderMethodProgress(d, i, metadata?.methodStage);
      syncPlaybackButtons(id);
      scrollChat(thread);
      if (typed) {
        body.classList.add("is-typing");
        const chars = Array.from(text);
        for (let n = 1; n <= chars.length; n += 2) {
          if (!await ready(t)) return;
          renderMessageText(body, chars.slice(0, n + 1).join(""));
          scrollChat(thread);
          await wait(role === "user" ? 52 : 48);
        }
        body.classList.remove("is-typing");
      }
      if (t !== token) return;
      if (role === "user" && d.messages[i - 1]?.[0] === "question") {
        const question = $$("[data-role=question]", thread).at(-1);
        if (question) markQuestionAnswer(question, d.messages[i - 1][1]);
      }
      appendDocumentChips(node, metadata);
      scrollChat(thread);
      progress.set(id, i + 1);
      if (id === "meeting-notes") renderMeetingProgress(i + 1);
      renderMethodProgress(d, i + 1);
      syncPlaybackButtons(id, i + 1 === d.messages.length);
      if (!reduced.matches) await wait(role === "question" ? 700 : 170);
    }
    if (t !== token) return;
    $(".chat-compose div").textContent = "使用者輸入也會自動演出";
    $(".playback-announcement").textContent = id + " 示範對話已播放，可重播或繼續閱讀。";
    controls(true);
  }
  function complete(id = active) {
    id = sceneId(id);
    const d = sceneById.get(id);
    if (!d) return;
    progress.set(id, d.messages.length);
    play(id);
  }
  function pause() { paused = !paused; controls(); }
  function showStatusSkill(d, count) {
    const latest = d.messages.slice(0, count).reverse().find(([role]) => role === "skill");
    const name = latest?.[1].match(/\/[a-z][a-z0-9-]*/)?.[0];
    const indicator = $("#status-skill");
    indicator.hidden = !name;
    if (name) indicator.textContent = name;
  }
  function syncPlaybackButtons(id, finished = false) {
    $$(".playback-cta").forEach(button => button.classList.remove("is-playing", "is-complete"));
    const root = $("#demo-" + id);
    if (!root) return;
    $$(".playback-cta", root).forEach(button => {
      const step = button.closest(".method-stage, .meeting-flow-step");
      if (step?.classList.contains("is-done")) button.classList.add("is-complete");
      else if (step?.classList.contains("is-current") && !finished || !step && !finished) button.classList.add("is-playing");
      else if (!step && finished) button.classList.add("is-complete");
    });
  }
  function renderMethodProgress(d, count, inFlight) {
    const root = $("#demo-" + d.id);
    const current = inFlight || d.messages[Math.max(0, count - 1)]?.[2]?.methodStage || d.id;
    for (const node of $$("[data-method-stage]", root)) {
      const stage = node.dataset.methodStage;
      const indices = d.messages.flatMap((message, i) => (message[2]?.methodStage || d.id) === stage ? [i] : []);
      const done = indices.length && count > indices.at(-1);
      node.classList.toggle("is-current", current === stage);
      node.classList.toggle("is-done", Boolean(done));
    }
    const rail = $(".quality-rail, .handoff-rail", root);
    if (rail) {
      const stages = $$(':scope > .method-stage', rail);
      const currentIndex = stages.findIndex(stage => stage.classList.contains("is-current"));
      const currentStage = stages[currentIndex];
      const label = stage => stage?.querySelector(".quality-label, .handoff-label");
      const fromTop = label => label ? Math.max(0, label.getBoundingClientRect().top + label.getBoundingClientRect().height / 2 - rail.getBoundingClientRect().top - 16) : 0;
      const finished = count === d.messages.length;
      const nextStage = !finished && stages[currentIndex + 1];
      const completedThrough = currentStage?.classList.contains("is-done") ? (nextStage || currentStage) : currentIndex > 0 ? currentStage : null;
      rail.style.setProperty("--rail-fill", (count ? fromTop(label(nextStage || currentStage)) : 0) + "px");
      rail.style.setProperty("--rail-done", fromTop(label(completedThrough)) + "px");
    }
  }
  function renderMeetingProgress(count, inFlight) {
    const { states, current } = meetingPlaybackState(count, inFlight);
    const root = $(".meeting-workflow");
    root.dataset.currentStage = current;
    for (const stage of $$("[data-meeting-step]", root)) {
      const id = stage.dataset.meetingStep, state = states[id];
      stage.dataset.flowState = state;
      stage.classList.toggle("is-current", id === current);
      stage.classList.toggle("is-done", state === "done");
      for (const output of $$(".workflow-output", stage)) {
        const visible = state === "done" || state === "preview";
        if (visible && !output.classList.contains("is-revealed")) restartPreview(output.closest(".document-preview"));
        output.classList.toggle("is-revealed", visible);
        output.setAttribute("aria-hidden", String(!visible));
        output.inert = !visible;
      }
    }
    const written = states["create-tasks"] === "done";
    $("[data-task-write-status]", root).textContent = written ? "Notion 寫入完成" : "候選任務 · 尚未寫入";
    $("[data-task-new-status]", root).textContent = written ? "✓ 已新建" : "待新建";
    $("[data-task-link-status]", root).textContent = written ? "↗ 已連結" : "待連結";
  }
  function restartPreview(card) {
    if (!card || reduced.matches) return;
    card.classList.remove("is-preview-typing");
    void card.offsetWidth;
    card.classList.add("is-preview-typing");
  }
  const previewObserver = new IntersectionObserver(entries => {
    for (const entry of entries) {
      if (entry.isIntersecting) restartPreview(entry.target);
      else entry.target.classList.remove("is-preview-typing");
    }
  }, { threshold: 0.18 });
  $$(".document-preview").forEach(card => {
    const lines = $$(".preview-code-line, .meeting-source > p, .method-notes dt, .method-notes dd, .method-tasks > small, .method-tasks > div, .method-tasks > p, .method-workspace > div", card);
    lines.forEach((line, index) => {
      line.classList.add("preview-type-line");
      line.style.setProperty("--preview-delay", Math.min(index * 130, 1300) + "ms");
    });
    previewObserver.observe(card);
  });
  // Keep headings readable without JavaScript or reduced motion; reveal their
  // existing text only when the reader reaches them, without changing layout.
  if (!reduced.matches) {
    const headingTimers = new WeakMap();
    const finishHeading = heading => {
      clearInterval(headingTimers.get(heading));
      headingTimers.delete(heading);
      heading.classList.remove("is-title-typing");
      $$(".title-type-glyph", heading).forEach(glyph => glyph.classList.remove("is-revealed"));
    };
    const headingObserver = new IntersectionObserver(entries => {
      for (const { target, isIntersecting } of entries) {
        if (!isIntersecting) { finishHeading(target); continue; }
        if (headingTimers.has(target)) continue;
        const glyphs = $$(".title-type-glyph", target);
        if (!glyphs.length) continue;
        target.classList.add("is-title-typing");
        let index = 0;
        const reveal = () => {
          glyphs[index++].classList.add("is-revealed");
          if (index === glyphs.length) finishHeading(target);
        };
        reveal();
        if (index < glyphs.length) headingTimers.set(target, setInterval(reveal, Math.max(18, Math.min(42, 950 / glyphs.length))));
      }
    }, { threshold: 0.18 });
    $$("#story-panel h2").forEach(heading => {
      const label = heading.textContent.trim();
      const walker = document.createTreeWalker(heading, NodeFilter.SHOW_TEXT);
      const nodes = [];
      while (walker.nextNode()) nodes.push(walker.currentNode);
      for (const node of nodes) {
        const fragment = document.createDocumentFragment();
        for (const character of Array.from(node.textContent)) {
          if (/\s/.test(character)) { fragment.append(document.createTextNode(character)); continue; }
          const glyph = document.createElement("span");
          glyph.className = "title-type-glyph";
          glyph.setAttribute("aria-hidden", "true");
          glyph.textContent = character;
          fragment.append(glyph);
        }
        node.replaceWith(fragment);
      }
      heading.setAttribute("aria-label", label);
      headingObserver.observe(heading);
    });
  }
  renderMeetingProgress(0);
  function readingPosition() {
    if (frame || changingLayout || editorTab !== "story") return;
    frame = requestAnimationFrame(() => {
      frame = 0;
      if (editorTab !== "story") return;
      const top = mobile.matches ? 76 : $(".editor__scroll").getBoundingClientRect().top;
      const panels = $$("[data-scene-panel]");
      const current = panels.filter(p => p.getBoundingClientRect().top <= top + 145).at(-1) || panels[0];
      const id = current.dataset.scenePanel;
      if (id === "welcome") { if (active) clear(); }
      else if (id !== active) play(id, true);
    });
  }
  function jump(id) {
    id = sceneId(id);
    const panel = id === "welcome" ? $("#welcome") : $("#demo-" + id);
    if (!panel) return;
    selectEditorTab("story", false);
    if (mobile.matches) panel.scrollIntoView({ behavior: "instant", block: "start" });
    else {
      const scroller = $(".editor__scroll");
      scroller.scrollTo({ top: scroller.scrollTop + panel.getBoundingClientRect().top - scroller.getBoundingClientRect().top, behavior: "instant" });
    }
    if (id === "welcome") clear();
    else if (active !== id) play(id, true);
  }
  function setPanel(name, visible) {
    document.body.classList.toggle(name === "explorer" ? "explorer-collapsed" : "chat-collapsed", !visible);
    $$('[data-toggle-panel="' + name + '"]').forEach(button => {
      button.setAttribute("aria-expanded", String(visible));
      const label = name === "explorer" ? (visible ? "收合檔案總管" : "展開檔案總管") : (visible ? "收合對話欄" : "展開對話欄");
      button.setAttribute("aria-label", label);
      button.title = label;
    });
    if (name === "explorer") $('.activitybar__button[data-toggle-panel="explorer"]').classList.toggle("is-active", visible);
    readingPosition();
  }
  $$('[data-toggle-panel]').forEach(button => button.addEventListener("click", () => {
    const name = button.dataset.togglePanel;
    const collapsed = document.body.classList.contains(name === "explorer" ? "explorer-collapsed" : "chat-collapsed");
    setPanel(name, collapsed);
  }));
  $$("[data-scene]").forEach(link => link.addEventListener("click", event => {
    event.preventDefault();
    const skill = link.dataset.scene, id = sceneId(skill);
    jump(skill);
    if (skill !== id && sceneById.get(id)?.stageStarts?.[skill] !== undefined) {
      progress.set(id, sceneById.get(id).stageStarts[skill]);
      play(id);
    }
  }));
  $$("[data-jump]").forEach(button => button.addEventListener("click", () => {
    if (button.dataset.jump === "workflow") jump("wrap-up");
    else if (mobile.matches && active) $("#demo-" + active + " .inline-demo").scrollIntoView({ behavior: "smooth" });
    else if (button.dataset.jump === "chat") setPanel("chat", true);
  }));
  $$("[data-demo-replay]").forEach(button => button.addEventListener("click", () => {
    const id = button.dataset.demoReplay;
    if (!mobile.matches) setPanel("chat", true);
    play(id, true);
    if (mobile.matches) $("#demo-" + id + " .inline-demo").scrollIntoView({ behavior: "instant", block: "start" });
  }));
  document.addEventListener("click", event => {
    const methodJump = event.target.closest("[data-method-jump]");
    if (methodJump) { jump(methodJump.dataset.methodJump); return; }
    const methodButton = event.target.closest("[data-method-play]");
    if (methodButton) {
      const id = methodButton.dataset.methodScene, stage = methodButton.dataset.methodPlay;
      if (editorTab !== "story") selectEditorTab("story", false);
      if (!mobile.matches) setPanel("chat", true);
      progress.set(id, sceneById.get(id).stageStarts?.[stage] || 0);
      play(id);
      if (mobile.matches) $("#demo-" + id + " .inline-demo").scrollIntoView({ behavior: "instant", block: "start" });
      return;
    }
    const stageButton = event.target.closest("[data-play-stage]");
    if (stageButton) {
      const stage = stageButton.dataset.playStage;
      if (!Object.hasOwn(meetingStarts, stage)) return;
      if (editorTab !== "story") selectEditorTab("story", false);
      if (!mobile.matches) setPanel("chat", true);
      if (active !== "meeting-notes") jump("meeting-notes");
      progress.set("meeting-notes", meetingStarts[stage]);
      play("meeting-notes");
      if (mobile.matches) $("#demo-meeting-notes .inline-demo").scrollIntoView({ behavior: "instant", block: "start" });
      return;
    }
    const link = event.target.closest("[data-demo-document]");
    if (!link) return;
    event.preventDefault();
    openDocument(link.dataset.demoDocument);
  });
  $(".chat-reset").addEventListener("click", () => { if (active) play(active, true); });
  $(".chat-complete").addEventListener("click", () => complete());
  $(".chat-pause").addEventListener("click", pause);
  $$("[data-inline-complete]").forEach(b => b.addEventListener("click", () => complete(b.dataset.inlineComplete)));
  $$("[data-inline-replay]").forEach(b => b.addEventListener("click", () => play(b.dataset.inlineReplay, true)));
  $$("[data-inline-pause]").forEach(b => b.addEventListener("click", pause));
  $(".theme-toggle").addEventListener("click", () => {
    document.body.classList.toggle("light");
    const next = document.body.classList.contains("light") ? "原版深色" : "Catppuccin Latte";
    $(".theme-toggle").setAttribute("aria-label", "切換至 " + next);
    $(".theme-toggle").title = "切換至 " + next;
  });
  $(".editor__scroll").addEventListener("scroll", readingPosition, { passive: true });
  window.addEventListener("scroll", readingPosition, { passive: true });
  window.addEventListener("resize", readingPosition);
  mobile.addEventListener("change", () => {
    const id = active;
    changingLayout = true;
    requestAnimationFrame(() => {
      if (!mobile.matches) window.scrollTo({ top: 0, behavior: "instant" });
      if (id && editorTab === "story") { jump(id); play(id); }
      changingLayout = false;
      readingPosition();
    });
  });
  reduced.addEventListener("change", () => { if (active && reduced.matches) complete(); readingPosition(); });
  clear();
  if (location.hash.startsWith("#demo-")) jump(location.hash.slice(6));
  readingPosition();
})();
