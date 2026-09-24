---
session: current Codex session
---

# create-tasks：保留已確認的設計 Plan

# Description

- 本次 refinement 來自實際建立「共用 AI Prompt Registry」task 時的落差：設計討論已形成具體方案，但建立 task 時只留下重新整理過的 Context／目標／驗收摘要，沒有保留原本的方案與取捨。
- 使用者指定套用 refinement suggestion 3，範圍只限 `create-tasks` skill。

# Changes Made

- 新增 design-discussion carryover：使用者已選定或核准方案時，把該段設計文字視為 task 來源資料。
- 在 commitment extraction 階段擷取 approved design plan，保留原文、標題層級與 trade-offs，不從尚未選定的選項推定核准。
- CREATE 預覽會顯示選用的 `# Plan`；建立 Notion task 時，將核准的設計內容原樣放入獨立的 `# Plan` 區段。
- 摘要可以補充但不能取代 `# Plan`；LINK 既有 task 仍只允許更新 `# Context`，不碰既有 `# Plan`。

# Verification

- `git diff --check -- skills/create-tasks/SKILL.md`：通過。
- 人工核對規則已同時涵蓋來源辨識、plan preview、CREATE body template 與 hard constraints。
- repo 原有的未提交差異不屬於本次變更；後續提交只會納入本報告與上述 refinement hunks。

# Result

- 未來從已完成的設計討論建立 task 時，原始設計方案與取捨會被保存在 `# Plan`，不再只剩 agent 改寫後的摘要。
