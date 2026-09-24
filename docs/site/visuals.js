// Code-native illustrations: each skill tells a story, not just a list of steps.
window.devSkillsVisual = (demo, preview) => {
  const symbols = {
    "⌘": '<path d="M8 3v5m8-5v5M6 8h12v3a6 6 0 0 1-12 0zm6 9v4"/>',
    "N": '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v7c0 4 16 4 16 0V5M4 12v7c0 4 16 4 16 0v-7"/>',
    "☷": '<path d="M6 3h9l4 4v14H6zM15 3v5h4M9 12h7M9 16h5"/>',
    "✓": '<path d="m5 12 4 4L19 6"/>'
  };
  const glyph = icon => symbols[icon] ? '<svg viewBox="0 0 24 24" aria-hidden="true">' + symbols[icon] + '</svg>' : icon;
  const node = (icon, title, caption, tone = "") => '<div class="picture-node ' + tone + '"><i aria-hidden="true">' + glyph(icon) + '</i><b>' + title + '</b><small>' + caption + '</small></div>';
  const arrow = label => '<div class="picture-arrow"><span>→</span><small>' + label + '</small></div>';
  const flow = (a, label, b) => '<div class="picture-flow">' + a + arrow(label) + b + '</div>';
  const beforeAfter = (before, after) => '<div class="picture-compare"><div class="picture-before"><span>原本</span>' + before + '</div><div class="picture-arrow"><span>→</span></div><div class="picture-after"><span>接起來以後</span>' + after + '</div></div>';
  const doc = (name, lines, tone = "") => {
    const id = name === "本地會議" ? "meeting-notes" : name === "本輪報告" ? "report" : demo.id;
    return preview(id, name);
  };
  const all = {
    "meeting-notes": flow('<div class="picture-chat"><span>「庫存只有 12 件。」</span><span>「可以取消吧？」</span><span>「缺貨通知下次聊。」</span></div>', "整理，不補猜測", doc("會議記錄", ["<b>✓ 已決定</b>　預留與取消", "<b>？待確認</b>　缺貨通知", "<b>↗ 原文</b>　討論有保留"])),
    "setup-notion": '<div class="picture-hub" role="group" aria-label="團隊專案連著任務庫與會議庫；會議決定經確認後可以接成任務"><svg class="hub-relations" viewBox="0 0 320 250" preserveAspectRatio="none" aria-hidden="true"><path class="hub-relation hub-relation--tasks" d="M160 96 L48 154"/><path class="hub-relation hub-relation--meetings" d="M160 96 L272 154"/><path class="hub-relation hub-relation--handoff" d="M224 202 H98"/><path class="hub-relation-arrow" d="m104 198 -6 4 6 4"/></svg>' + node("⌘", "團隊的專案", "共用入口") + '<div class="hub-branches">' + node("N", "任務庫", "追工作與進度", "tone-mint") + node("☷", "會議庫", "留討論與決定", "tone-blue") + '</div><p class="hub-link-note">會議裡確認的事，接成任務</p><p class="picture-caption">設定一次，以後不用每次再貼連結。</p></div>',
    "upload-meeting": flow(doc("本地會議", ["整理後的記錄", "原始逐字稿"]), "一起帶過去", node("N", "Notion 會議", "同事也看得到", "tone-mint")),
    "create-tasks": '<div class="task-branch"><div class="branch-source">' + node("☷", "這次會議", "不是每句話都變成任務") + '</div><div class="branch-results"><article><span class="task-symbol new">＋</span><div><b>新建</b><p>庫存預留與取消</p></div></article><article><span class="task-symbol link">↗</span><div><b>連回原任務</b><p>員工登入，不重複開單</p></div></article><article><span class="task-symbol later">…</span><div><b>先略過</b><p>缺貨通知還沒決定</p></div></article></div></div>',
    "sync": '<div class="flow-visual"><div class="flow-node"><span>你</span><b>自己的分支</b><small>先保住本地修改</small></div><div class="flow-connector"><i></i><small>fetch</small></div><div class="flow-node"><span>隊友</span><b>最新進度</b><small>取回遠端版本</small></div><div class="flow-connector"><i></i><small>merge</small></div><div class="flow-node flow-node--safe"><span>共同狀態</span><b>可以開工了</b><small>✓ 確認沒有衝突</small></div></div><div class="guardrail"><div class="guardrail__icon">!</div><div><b>遇到衝突，它會停下來。</b><p>不猜、不偷偷刪改動，也不使用 <code>reset --hard</code>。把確切情況交還給人判斷。</p></div></div>',
    "fetch-task": flow(node("N", "Notion 任務", "背景與選定方案", "tone-mint"), "帶進工作區", doc("本地 task", ["<b class=\"fresh\">↻ Context 更新</b>", "<span>Plan 原樣保留</span>", "<span>Notes 原樣保留</span>"])),
    "discuss": '<div class="decision-picture"><div class="decision-question"><span>？</span><b>只剩 1 件，兩位同事同時預留？</b></div><div class="decision-options"><article><small>A</small><b>只看畫面</b><p>快一點，但可能超賣</p></article><article class="selected"><small>B · 選定 ✓</small><b>送出時確認庫存</b><p>多一道處理，守住可用數量</p></article></div><p class="picture-caption">方向由你選；Claude 把取捨講清楚。</p></div>',
    "verify": '<div class="verification-picture" data-visual-kind="test-fix-loop"><ol class="verify-cycle"><li><span aria-hidden="true">▶</span><b>跑測試</b><small>照既有計畫執行</small></li><li><span aria-hidden="true">↗</span><b>修正失敗</b><small>找到原因，修改程式</small></li><li><span aria-hidden="true">↻</span><b>重新驗證</b><small>確認修正真的有效</small></li></ol><div class="verify-repeat"><span aria-hidden="true">↶</span> 還沒過，就再修正、再重跑</div><p class="verify-passed"><span aria-hidden="true">✓</span> 測試通過，才完成這輪驗證</p><p class="verify-blocked">若環境或設定卡住，會說明阻礙，不把未測當作通過。</p></div>',
    "update-docs": beforeAfter('<p><s>隨時可以取消</s></p><small>舊說明已經跟程式不同。</small>', doc("先看修改提案，再決定要不要套用", [])),
    "code-review": '<div class="review-handoff"><code>這一輪的修改</code><span>↓ 六個角色分頭看，再帶著證據回來</span></div>',
    "report": '<div class="report-picture" data-visual-kind="paper-stack"><div class="report-ingredients report-stack"><span>☷ 當時的決定</span><span>⑂ 實際修改</span><span>✓ 驗證證據</span><span>… 未完成事項</span></div><div class="evidence-link"><span aria-hidden="true">→</span><small>一起留下</small></div>' + doc("交接報告", ["做了什麼、為什麼這樣做", "怎麼確認、還有什麼没做", "<b>下一個人不用重新猜</b>"], "tone-mint") + '</div>',
    "rename-session": beforeAfter('<div class="session-window"><span>⌘</span> New conversation<small>這是哪一個？</small></div>', '<div class="session-window"><span>⌘</span> 庫存預留與取消<small>跟報告的主題一致</small></div>'),
    "wrap-up": '<div class="wrap-picture"><div class="wrap-origin">今天的工作</div><div class="wrap-fork"><span>↙ Quick</span><span>Full ↘</span></div><div class="wrap-destinations"><div>先收好進度</div><div>完整檢查與交付</div></div><p class="picture-caption">兩條路都要交代：存好了嗎？送出了嗎？部署了嗎？</p></div>',
    "sync-report": '<div class="handoff-picture">' + flow(doc("本輪報告", ["完成：預留、取消", "待做：查詢改善", "證據：操作與測試"]), "送回原任務", node("N", "Testing", "結果已回填，等團隊試用", "tone-mint")) + '<div class="handoff-state"><span>⑂ GitHub · PR 等待 review</span><span>N Notion · 任務待驗收</span></div></div>',
    "find-session": '<div class="memory-picture"><div class="memory-search">⌕　取消預留</div><div class="timeline"><div class="timeline__item"><time>昨天</time><i></i><div><b>討論</b><p>出貨後不能自己取消</p></div></div><div class="timeline__item"><time>後來</time><i></i><div><b>修改與驗證</b><p>取消失敗，保留原本的預留狀態</p></div></div><div class="timeline__item timeline__item--next"><time>今天</time><i></i><div><b>接著做</b><p>倉管代取消仍待確認，不用重猜</p></div></div></div></div>',
    "improve": '<div class="improve-picture">' + beforeAfter('<p>「驗證通過。」</p><small>但是，到底測了什麼？</small>', '<p>操作 → 觀察 → 未測範圍</p><small>把提醒留進團隊共用規則</small>') + '<div class="improve-loop">↶ 下一次工作，從改好的流程開始</div></div>'
  };
  return '<div class="skill-visual visual-' + demo.id + '" role="group" aria-label="' + demo.id + ' 圖解">' + all[demo.id] + '</div>';
};
