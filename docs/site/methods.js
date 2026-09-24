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
    ${stage("sync", title(["sync"], "同事已經改了程式，自己若還在舊版上做，很容易白忙一場。先保住手上的修改，再接進團隊最新進度；遇到衝突就停下來一起看。") + window.devSkillsVisual({ id: "sync" }, preview) + action("sync", "sync"))}
    <div class="prepare-junction"><span>${icon("branch")}團隊最新程式</span><b aria-hidden="true">＋</b><span>${icon("file")}任務背景</span><p>帶著同一份現況，一起討論做法</p></div>
    ${stage("discuss", title(["discuss"], "一句需求可以有好幾種做法，太快開工，常常做完才發現不是大家要的。先把選項和代價講清楚，由你選定方向，再留下計畫。") + `<div class="method-split"><div class="method-options"><div><small>做法 A</small><b>先完成眼前需要</b><p>改動較小，也要交代暫時沒顧到的部分。</p></div><div><small>做法 B</small><b>一起處理後續需要</b><p>投入多一點，確認值得做，再往下走。</p></div><p class="method-decision">由你確認方向，留下計畫再動手。</p></div>${preview("discuss")}</div>` + action("discuss", "fetch-task"))}
  </div>`;
  if (demo.id === "verify") return `<div class="method-layout method-quality">
    <div class="quality-rail" aria-label="測試修正、校準文件、六個角色檢查的連續流程">
      ${stage("verify", `<div class="quality-label">測試</div><div class="quality-body">${title(["verify"], "「看起來可以用」還不夠，修改也可能讓原本能用的地方壞掉。照計畫真的跑測試；失敗就修、修完再跑，不把沒測過說成通過。")}<div class="method-split">${window.devSkillsVisual({ id: "verify" }, preview)}${preview("discuss")}</div>${action("verify", null)}<p class="quality-next">結果確認後，接著檢查說明有沒有跟上</p></div>`)}
      ${stage("update-docs", `<div class="quality-label">文件</div><div class="quality-body">${title(["update-docs"], "程式已經變了，舊文件卻可能還在教人照舊做，下一個人就容易走錯。找出這輪真正影響到的說明，確認後只更新那些地方。")}<div class="method-split"><div class="docs-alignment"><div><span>程式</span><b>這輪實際的行為</b></div><span class="alignment-mark" aria-hidden="true">⇄</span><div><span>文件</span><b>接手的人會讀到的說明</b></div><p>只校準有受影響的地方，不順手重寫整份。</p></div>${preview("update-docs")}</div>${action("update-docs", null)}<p class="quality-next">說明對齊後，再換幾個角度看這輪修改</p></div>`)}
      ${stage("code-review", `<div class="quality-label">複查</div><div class="quality-body">${title(["code-review"], "自己剛寫完的程式，最難看出自己的盲點。六個角色分頭檢查同一輪修改，帶著證據指出問題；每條意見再決定修好、延後或不採納。")}<div class="review-table-center">同一輪修改 <span>六個不同角度</span></div><div class="method-review-team"></div><div class="method-split review-resolution"><div class="review-routing"><h4>每個問題，都有去處</h4><div class="review-routing__routes"><div class="review-routing__route review-routing__route--fix"><span class="review-routing__mark" aria-hidden="true">↶</span><div><b>這輪修好</b><p>回到驗證，重跑確認。</p></div></div><div class="review-routing__route review-routing__route--defer"><span class="review-routing__mark" aria-hidden="true">↗</span><div><b>確認後延後</b><p>記下原因與待辦，帶進交接報告。</p></div></div><div class="review-routing__route review-routing__route--decline"><span class="review-routing__mark" aria-hidden="true">−</span><div><b>不採納</b><p>說明理由，不把建議照單全收。</p></div></div></div></div>${preview("code-review")}</div>${action("code-review", null)}</div>`)}
    </div>
  </div>`;
  if (demo.id === "report") return `<div class="method-layout method-handoff">
    <div class="handoff-rail" aria-label="成果、版本、團隊進度、下次接手">
      ${stage("report", `<div class="handoff-label">成果</div><div class="handoff-body">${title(["report", "rename-session"], "過幾天只看到一句「做完了」，很難知道做了多少、還缺什麼。把成果、驗證和未完成事項寫進報告，也替對話取個找得到的名稱，讓下一輪接得上。")}<div class="method-split"><div class="handoff-summary" aria-label="報告留下完成範圍、驗證證據與接續事項"><p class="handoff-summary__lead">交接時，留下三個找得到的答案</p><div class="handoff-summary__track"><div><span class="handoff-summary__mark">01</span><span><b>完成範圍</b><small>做了什麼，為什麼這樣選</small></span></div><div><span class="handoff-summary__mark">02</span><span><b>驗證證據</b><small>真的跑過哪些檢查，結果如何</small></span></div><div><span class="handoff-summary__mark">03</span><span><b>接續事項</b><small>還沒做、還在等誰確認</small></span></div></div><p class="handoff-summary__outcome"><span aria-hidden="true">↗</span> 收進同一份報告，下一輪直接接著讀</p></div>${preview("report")}</div>${action("report", null)}</div>`)}
      ${stage("delivery", `<div class="handoff-label">版本</div><div class="handoff-body">${title(["wrap-up"], "幾個人或視窗一起改程式時，最怕把別人的未完成修改順手提交。先清理暫存檔、確認範圍，再把這輪存成版本；需要清除的會先問你。")}<div class="delivery-trunk"><b>cleanup + commit</b><div class="delivery-choices"><span>開 PR<small>請隊友一起看</small></span><span>直接 push<small>確認後送到遠端</small></span><span>保留本地<small>今天先存好</small></span></div><p>提交後再選怎麼交付；已 commit、已 push、已部署，分開交代。</p></div>${action("delivery", "wrap-up")}</div>`)}
      ${stage("sync-report", `<div class="handoff-label">團隊</div><div class="handoff-body">${title(["sync-report"], "程式有了新版本，Notion 任務若還停在昨天，團隊就不知道現在能不能驗收。先找對任務，再帶回報告、版本連結和建議狀態；你確認後才寫入，寫完再核對。")}<div class="method-split"><div class="notion-return" aria-label="對準任務、確認欄位、補入新內容並核對"><div class="notion-return__step"><small>01 · 找對地方</small><b>連過的任務直接接上；沒連過的先請你選</b></div><div class="notion-return__step"><small>02 · 確認任務狀態</small><b>依報告建議「測試中」或「已完成」等狀態</b><span>你確認後才改；GitHub 連結只補空白欄位</span></div><div class="notion-return__step"><small>03 · 寫回 Notion</small><b>把確認的狀態、連結與新報告內容寫進任務</b><span>寫完重新核對；重跑時只補新段落，不重複貼</span></div></div>${preview("sync-report")}</div>${action("sync-report", null)}</div>`)}
      ${stage("resume", `<div class="handoff-label">接手</div><div class="handoff-body">${title(["find-session"], "隔天接手的人不只想知道「做完沒」，也可能要查「當時為什麼這樣選」。先看報告裡的待辦，需要來龍去脈時，再用線索找回原對話。")}<div class="handoff-return">成果 → 版本 → 團隊進度 <b>↶ 回到下一次開工</b></div>${action("resume", "find-session")}<button class="method-crosslink" type="button" data-method-jump="find-session">看看 Memory 怎麼保存這些脈絡 →</button></div>`)}
    </div>
  </div>`;
  if (demo.id === "find-session") return `<div class="method-layout method-memory">
    <p class="memory-question">「接下來做什麼？」和「當時為什麼這樣做？」需要看的資料不一樣。</p>
    <div class="memory-architecture" aria-label="團隊、工作區與原始對話三層記憶">
      <article class="memory-tier memory-tier--team"><div class="memory-tier__copy"><span class="memory-layer">團隊共用</span><h3>Notion 任務與會議</h3><p>誰在做什麼、決定了什麼、現在走到哪裡，讓大家看同一份進度。</p><a href="document.html?skill=sync-report" data-demo-document="sync-report">查看文件 ↗</a></div><div class="memory-database" aria-hidden="true"><span>任務</span><b>需求與負責人</b><b>最新進度</b><span>會議</span><b>討論與決定</b><b>後續工作</b></div></article>
      <div class="memory-transfer"><span>背景帶進工作區 ↓</span><span>↑ 結果回到團隊</span></div>
      <article class="memory-tier memory-tier--work"><div class="memory-tier__copy"><span class="memory-layer">這輪工作</span><h3>收成一份交接報告</h3><p>任務的 Context 與選好的 Plan 一起帶進報告，再補上這輪實際修改、驗證結果和待接事項。</p></div><div class="memory-workflow"><div class="memory-workflow__input"><span>Context</span><span>Plan</span></div><span class="memory-workflow__arrow" aria-hidden="true">↓</span><div class="memory-report-sheet"><b>report.md</b><div><span># Context</span><span># Plan</span><span># Changes Made</span><span># Verification</span><span># Result</span><span># Updates <small>有後續時</small></span><span># Unsolved Issues <small>有未解問題時</small></span></div><a href="document.html?skill=report" data-demo-document="report">查看文件 ↗</a></div></div></article>
      <div class="memory-transfer memory-transfer--deep"><span>回看對話，分析哪一步需要改進 ↓</span></div>
      <article class="memory-tier memory-tier--session"><div class="memory-tier__copy"><span class="memory-layer">原始來回</span><h3>Session log</h3><p>保留對話、選擇與修正過程，方便回看互動、分析卡點。它是原始材料，不取代已整理好的交接報告。</p></div><div class="memory-transcript" aria-hidden="true"><span><i>你</i>提出需求與限制</span><span><i>AI</i>比較做法、執行檢查</span><span><i>你</i>確認取捨</span></div></article>
    </div>
    ${stage("find-session", `<div class="method-split memory-lookup"><div>${title(["find-session"], "知道某個決定聊過，卻忘了在哪個視窗？用主題或改過的檔案找回線索，不靠 AI 猜昨天發生什麼。")}<p>先讀摘要決定是否相關，再打開原紀錄核對。</p>${action("find-session", null)}<button class="method-crosslink" type="button" data-method-jump="report">回到 Handoff 流程 →</button></div>${preview("find-session")}</div>`)}
  </div>`;
  if (demo.id === "improve") return `<div class="method-layout method-improve">
    ${title(["improve"], "如果同一個提醒每輪都要再說一次，光靠人記住也不是辦法。回看這輪對話與 review，找出哪一步反覆卡住，再由你決定什麼改法值得留給下一輪。")}
    <div class="learning-route" aria-label="從這輪對話到下輪改進的四個步驟">
      <div class="learning-steps">${stage("friction", icon("question") + '<span>哪一步卡住？</span><p>指回這輪真的發生的事，不憑空發明問題。</p>')}${stage("cause", icon("search") + '<span>怎樣改才有用？</span><p>把失敗的步驟和具體改法擺在一起，讓你判斷值不值得留下。</p>')}${stage("choose", icon("choice") + '<span>收進哪裡？</span><p>由你決定提醒的適用範圍，避免放錯地方。</p>', "learning-decision")}${stage("apply", icon("repeat") + '<span>下輪用得上</span><p>你確認後才修改；下一輪真的會讀到。</p>')}</div>
      <div class="learning-destinations" aria-label="收進哪裡的分流選項"><span><b>Skill</b><small>流程每次都該用</small></span><span><b>團隊／專案規則</b><small>只在這裡適用</small></span><span><b>程式旁註解</b><small>只提醒這個位置</small></span><span><b>個人偏好</b><small>留給自己</small></span><span><b>略過</b><small>不值得變成規則</small></span></div>
    </div>
  </div>`;
  return "";
};
