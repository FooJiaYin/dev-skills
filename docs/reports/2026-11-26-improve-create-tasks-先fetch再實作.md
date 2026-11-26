---
session: 2026-11-26-只填規格報價時台幣成本試算消失 (ee667c6b-c0fb-441a-8e3f-965d481e77f0)
---

# improve：create-tasks 核准時要求直接實作，先 /fetch-task 再派工

# Description

- sparktoy 佩芳驗收回饋：`/create-tasks` 建了兩張任務，使用者回「create all, 用 subagent 個別修」。直接派實作 agent，§10 的 checkout picker 被跳過，兩張任務沒有本機 `docs/tasks/<slug>.md`；部署後使用者問「fetched tasks?」才補 fetch，報告與 `/sync-report` 才有對象。

# Changes Made

- `skills/create-tasks/SKILL.md` §10：核准同時要求立即實作時，不跳 picker、直接對所有建立／連結的任務跑 `/fetch-task`，再派實作。

# Result

- 下次「建票＋立刻修」的流程會先有任務檔，報告可逐任務寫、可同步。
