# code-review skill：加入 whole-tree（tree）模式與「取代 built-in」註記

# Description

- 在 sparktoy-erp 跑 `/code-review` 時，使用者要的是「審核現在的前端架構、有沒有大量重複」，但 skill 只會 `git diff BASE..HEAD`，scorer 又把「pre-existing」「unmodified lines」自動判 0 分。當場改寫了流程；本報告把那個改寫落到 skill 本身。

# Changes Made

- `skills/code-review/SKILL.md`
  - frontmatter description：加入 tree mode 觸發詞（`/code-review tree [glob]`、「審核架構／有沒有重複」）與「Supersedes the built-in /code-review — invoke only this one」。
  - `## Inputs` 新增 **Tree mode** 段：不 diff、scope = glob（預設 `src/**`）、Phase 2 改為「每個頂層區域一個 quality-architecture agent ＋ 一個跨區重複掃描 agent ＋ claude-md」（bugs/performance 可選，git-history/plan-adherence 略過）、要求每條重複 finding 列出**所有**位置與建議抽象；Phase 3 rubric 原文照傳，另加覆寫：false-positive 第 1、8 類在 tree mode 不適用。
  - 新增「同一 session 只跑一個 review orchestrator；若 built-in finder 已在跑，把它們的報告併入 finding pool，不要重新 fan-out」。

Result: 已寫入；未改 `agents/*.md`（現有 prompt 以 `{BASE}..{HEAD}` 為主，tree mode 下由 orchestrator 覆寫框架即可）。

# Result

- 本次在 sparktoy-erp 的實跑：5 個區域／跨區 agent ＋ 併入 built-in 的 8 個 finder → 54 候選 → 54 個 Haiku scorer → 53 條進 `REVIEW.md`。tree mode 描述即以此為藍本。
- 同 session 另兩項改進落在別處：sparktoy-erp `AGENTS.md`（本地時區日期規則）、`~/.claude/CLAUDE.md`（絕對路徑規則擴到 `>`／`>>`）。

# TODO

- `agents/quality-architecture.md` 可加一段 tree-mode 版 Inputs（目前靠 orchestrator 內嵌 prompt）。
