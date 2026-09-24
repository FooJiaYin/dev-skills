// Each composition explains a working method. Documents support its outcomes.
window.devSkillsMethod = (demo, preview) => {
  const drawings = {
    branch: '<circle cx="6" cy="5" r="2"/><circle cx="6" cy="19" r="2"/><circle cx="18" cy="5" r="2"/><path d="M6 7v10m12-10c0 7-12 3-12 10"/>',
    file: '<path d="M5 3h9l5 5v13H5zM14 3v6h5M9 13h6m-6 4h4"/>',
    question: '<path d="M4 4h16v12H9l-5 4zM10 8a2 2 0 1 1 3 2l-1 1m0 2h.01"/>',
    check: '<circle cx="12" cy="12" r="9"/><path d="m7 12 3 3 7-7"/>',
    next: '<path d="M4 12h15m-6-6 6 6-6 6"/>',
    search: '<circle cx="10" cy="10" r="6"/><path d="m15 15 6 6M7 10h6"/>',
    choice: '<path d="M12 21V11m0 0L5 4m7 7 7-7M5 10V4h6m2 0h6v6"/>',
    repeat: '<path d="M20 8a9 9 0 0 0-15-3L2 8m0-6v6h6m-4 8a9 9 0 0 0 15 3l3-3m0 6v-6h-6"/>'
  };
  const icon = name => `<svg class="method-symbol" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${drawings[name]}</svg>`;
  const stageCalls = {
    sync: "接上進度", discuss: "比較做法", verify: "重跑測試",
    "update-docs": "校準說明", "code-review": "六角度檢查",
    report: "留下成果", delivery: "整理並提交",
    "sync-report": "帶回任務", resume: "接回脈絡",
    "find-session": "找回對話", friction: "發現卡點",
    cause: "釐清原因", choose: "決定改法", apply: "用在下輪"
  };
  const stageSkills = {
    report: "report → /rename-session", delivery: "wrap-up", resume: "find-session",
    friction: "improve", cause: "improve", choose: "improve", apply: "improve"
  };
  const action = (stage, file, label = "看這一步怎麼做") => {
    // A process step is not automatically a document. Keep only genuine related artifacts.
    if (["sync", "rename-session", "wrap-up"].includes(file) || ["friction", "cause", "choose", "apply"].includes(stage)) file = null;
    const skill = stageSkills[stage] || stage;
    return `<div class="method-actions"><button type="button" class="playback-cta" data-method-scene="${demo.id}" data-method-play="${stage}"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m8 5 11 7-11 7z"/></svg><code class="cta-skill">/${skill}</code><span>${stageCalls[stage] || label}</span></button>${file ? `<a href="document.html?skill=${file}" data-demo-document="${file}">查看文件</a>` : ""}</div>`;
  };
  const title = (skills, text) => `<h3>${skills.map(id => `<code class="skill-name">/${id}</code>`).join('<span aria-hidden="true"> → </span>')}</h3><p class="method-explanation">${text}</p>`;
  const stage = (id, content, name = "") => `<div class="method-stage ${name}" data-method-stage="${id}">${content}</div>`;
  if (demo.id === "sync") return `<div class="method-layout method-prepare">
    ${stage("sync", title(["sync"], "先接好同事的進度，也保住自己還沒交出去的修改。") + window.devSkillsVisual({ id: "sync" }, preview) + action("sync", "sync"))}
    <div class="prepare-junction"><span>${icon("branch")}團隊最新程式</span><b aria-hidden="true">＋</b><span>${icon("file")}任務背景</span><p>帶著同一份現況，一起討論做法</p></div>
    ${stage("discuss", title(["discuss"], "先比較，再決定。讓取捨攤開來看，比寫完才發現方向不同更省事。") + `<div class="method-split"><div class="method-options"><div><small>做法 A</small><b>先完成眼前需要</b><p>改動較小，也要交代暫時沒顧到的部分。</p></div><div><small>做法 B</small><b>一起處理後續需要</b><p>投入多一點，確認值得做，再往下走。</p></div><p class="method-decision">由你確認方向，留下計畫再動手。</p></div>${preview("discuss")}</div>` + action("discuss", "fetch-task"))}
  </div>`;
  if (demo.id === "verify") return `<div class="method-layout method-quality">
    <div class="quality-rail" aria-label="測試修正、校準文件、六個角色檢查的連續流程">
      ${stage("verify", `<div class="quality-label">測試</div><div class="quality-body">${title(["verify"], "不是多寫一張清單，而是照計畫真的跑；失敗就回去修，再跑到確認為止。")}<div class="method-split">${window.devSkillsVisual({ id: "verify" }, preview)}${preview("discuss")}</div>${action("verify", null)}<p class="quality-next">結果確認後，接著檢查說明有沒有跟上</p></div>`)}
      ${stage("update-docs", `<div class="quality-label">文件</div><div class="quality-body">${title(["update-docs"], "程式改了，文件也要說同一件事。先找出受影響的說明，確認範圍後再更新。")}<div class="method-split"><div class="docs-alignment"><div><span>程式</span><b>這輪實際的行為</b></div><span class="alignment-mark" aria-hidden="true">⇄</span><div><span>文件</span><b>接手的人會讀到的說明</b></div><p>只校準有受影響的地方，不順手重寫整份。</p></div>${preview("update-docs")}</div>${action("update-docs", null)}<p class="quality-next">說明對齊後，再換幾個角度看這輪修改</p></div>`)}
      ${stage("code-review", `<div class="quality-label">複查</div><div class="quality-body">${title(["code-review"], "六個角色看同一輪修改，各自帶回問題和依據。不是湊六個通過，而是讓盲點有人接住。")}<div class="review-table-center">同一輪修改 <span>六個不同角度</span></div><div class="method-review-team"></div><div class="method-split review-resolution"><div class="review-routing"><h4>每個問題，都有去處</h4><div class="review-routing__routes"><div class="review-routing__route review-routing__route--fix"><span class="review-routing__mark" aria-hidden="true">↶</span><div><b>這輪修好</b><p>回到驗證，重跑確認。</p></div></div><div class="review-routing__route review-routing__route--defer"><span class="review-routing__mark" aria-hidden="true">↗</span><div><b>確認後延後</b><p>記下原因與待辦，帶進交接報告。</p></div></div><div class="review-routing__route review-routing__route--decline"><span class="review-routing__mark" aria-hidden="true">−</span><div><b>不採納</b><p>說明理由，不把建議照單全收。</p></div></div></div></div>${preview("code-review")}</div>${action("code-review", null)}</div>`)}
    </div>
  </div>`;
  if (demo.id === "report") return `<div class="method-layout method-handoff">
    <div class="handoff-rail" aria-label="成果、版本、團隊進度、下次接手">
      ${stage("report", `<div class="handoff-label">成果</div><div class="handoff-body">${title(["report", "rename-session"], "把成果、驗證和未完成事項寫進報告；存好後自動替對話取個找得到的名稱。下次接手，不必從一排視窗裡猜。")}<div class="method-split"><div class="handoff-summary" aria-label="報告留下完成範圍、驗證證據與接續事項"><p class="handoff-summary__lead">交接時，留下三個找得到的答案</p><div class="handoff-summary__track"><div><span class="handoff-summary__mark">01</span><span><b>完成範圍</b><small>做了什麼，為什麼這樣選</small></span></div><div><span class="handoff-summary__mark">02</span><span><b>驗證證據</b><small>真的跑過哪些檢查，結果如何</small></span></div><div><span class="handoff-summary__mark">03</span><span><b>接續事項</b><small>還沒做、還在等誰確認</small></span></div></div><p class="handoff-summary__outcome"><span aria-hidden="true">↗</span> 收進同一份報告，下一輪直接接著讀</p></div>${preview("report")}</div>${action("report", null)}</div>`)}
      ${stage("delivery", `<div class="handoff-label">版本</div><div class="handoff-body">${title(["wrap-up"], "先處理暫存檔、確認只包含這輪的修改，再 commit 成版本。需要清除的會先問你，別人的修改不一起帶走。")}<div class="delivery-trunk"><b>cleanup + commit</b><div class="delivery-choices"><span>開 PR<small>請隊友一起看</small></span><span>直接 push<small>確認後送到遠端</small></span><span>保留本地<small>今天先存好</small></span></div><p>提交後再選怎麼交付；已 commit、已 push、已部署，分開交代。</p></div>${action("delivery", "wrap-up")}</div>`)}
      ${stage("sync-report", `<div class="handoff-label">團隊</div><div class="handoff-body">${title(["sync-report"], "先對準正確的 Notion 任務，再把這輪報告接上去。會依結果建議任務狀態，也可補上版本連結；這些都先請你確認，寫完再核對。")}<div class="method-split"><div class="notion-return" aria-label="對準任務、確認欄位、補入新內容並核對"><div class="notion-return__step"><small>01 · 找對地方</small><b>連過的任務直接接上；沒連過的先請你選</b></div><div class="notion-return__step"><small>02 · 確認任務狀態</small><b>依報告建議「測試中」或「已完成」等狀態</b><span>你確認後才改；GitHub 連結只補空白欄位</span></div><div class="notion-return__step"><small>03 · 寫回 Notion</small><b>把確認的狀態、連結與新報告內容寫進任務</b><span>寫完重新核對；重跑時只補新段落，不重複貼</span></div></div>${preview("sync-report")}</div>${action("sync-report", null)}</div>`)}
      ${stage("resume", `<div class="handoff-label">接手</div><div class="handoff-body">${title(["find-session"], "下次從未完成事項接著做；想知道當時為什麼這樣選，再找回原對話，不必全部重講。")}<div class="handoff-return">成果 → 版本 → 團隊進度 <b>↶ 回到下一次開工</b></div>${action("resume", "find-session")}<button class="method-crosslink" type="button" data-method-jump="find-session">看看 Memory 怎麼保存這些脈絡 →</button></div>`)}
    </div>
  </div>`;
  if (demo.id === "find-session") return `<div class="method-layout method-memory">
    <p class="memory-question">「接下來做什麼？」和「當時為什麼這樣做？」需要看的資料不一樣。</p>
    <div class="memory-architecture" aria-label="團隊、工作區與原始對話三層記憶">
      <article><span class="memory-layer">團隊一起看</span><h3>Notion 任務與會議</h3><p>需求、決定、負責的工作和最新進度。先找到這件事，再往下看細節。</p><a href="document.html?skill=sync-report" data-demo-document="sync-report">查看文件</a></article>
      <div class="memory-layer-link">任務背景帶進來 ↑↓ 工作結果帶回去</div>
      <article><span class="memory-layer">在工作區接著做</span><h3>任務檔、計畫與報告</h3><p>任務檔留背景與筆記，計畫留選定的方向，報告留成果、證據和未完成事項。</p><div class="memory-file-links"><a href="document.html?skill=fetch-task" data-demo-document="fetch-task">task.md</a><a href="document.html?skill=discuss" data-demo-document="discuss">plan.md</a><a href="document.html?skill=report" data-demo-document="report">report.md</a></div></article>
      <div class="memory-layer-link">結果是入口，需要原因時再往下找</div>
      <article><span class="memory-layer">保留當時的來回</span><h3>Session log</h3><p>討論、選擇、工具活動與修正過程。它保留來龍去脈，不取代整理好的交接報告。</p><code class="skill-name">/rename-session → /find-session</code></article>
    </div>
    ${stage("find-session", `<div class="method-split memory-lookup"><div>${title(["find-session"], "記得主題或改過的檔案，就從線索找回對話；不用靠 AI 憑空記住昨天。")}<p>先讀摘要決定是否相關，再打開原紀錄核對。</p>${action("find-session", null)}<button class="method-crosslink" type="button" data-method-jump="report">回到 Handoff 流程 →</button></div>${preview("find-session")}</div>`)}
  </div>`;
  if (demo.id === "improve") return `<div class="method-layout method-improve">
    ${title(["improve"], "工作裡的卡點，不用靠人另外抄一本錯誤清單。回看這輪對話和 review 的結果，先找到具體是哪一步不順，再討論值得留下什麼。")}
    <div class="learning-evidence" aria-label="從這輪對話和 review 找出改進線索"><span>這輪對話<small>你的提醒與中途修正</small></span><span class="learning-evidence-plus" aria-hidden="true">＋</span><span>REVIEW.md<small>檢查時發現的問題</small></span><span class="learning-evidence-arrow" aria-hidden="true">↘</span></div>
    <div class="learning-cycle">${stage("friction", icon("question") + '<span>指出卡住的一步</span><p>不是只說「下次注意」，而是找出當時怎麼卡住。</p>' + action("friction", "improve"))}${stage("cause", icon("search") + '<span>提出具體改法</span><p>說清楚哪句規則、哪個順序需要改。</p>' + action("cause", "improve"))}${stage("choose", icon("choice") + '<span>你來決定去處</span><p>放進 skill、團隊規則、程式旁，或這次略過。</p>' + action("choose", "improve"), "learning-decision")}${stage("apply", icon("repeat") + '<span>確認後用在下輪</span><p>只改你同意的地方，讓下一次真的讀得到。</p>' + action("apply", "improve"))}<span class="learning-return" aria-hidden="true">↶</span></div>
    <div class="method-split"><p class="learning-note">值得留下的改法，當場放到會被讀到的位置；<br>不適用的就略過，不讓規則越堆越厚。</p>${preview("improve")}</div>
  </div>`;
  return "";
};
