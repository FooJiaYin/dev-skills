---
session: 產出區統一版型設計 (6edb7f2f-a58a-45db-bc46-4f9922f62859)
---
# design skill：打 `/design` 時接手內建 Artifact 指令

> 2026-11-21｜session 產出區統一版型設計（6edb7f2f）｜不屬於任何 Notion task；同 session 的主要工作見 sontis-ai `demo-bento` 分支 `docs/reports/2026-11-21-demo統一版型-便當格產出區-步驟列與style-lab.md`

## 摘要

| | 之前 ❌ | 之後 ✓ |
|---|---|---|
| 使用者打 `/design` | 進了內建 Artifact Design 指令（quickstart → 建 Artifact 並 publish） | description 寫明「`/design` 也用這個 skill」，載入 dev-skills design |
| 輸出位置 | 內建指令要求 publish Artifact，跟使用者 CLAUDE.md「HTML 預設本機、不 publish」衝突 | 本文寫明：內建 `/design` 的「publish Artifact」不算使用者要求 Artifact，照樣寫 `docs/design/` 本機 HTML |

## 起因

使用者在 sontis-ai 打 `/design 我覺得現在品牌卡、需求單…不好看而且不統一`，harness 解析成內建 Artifact `/design`。被問要本機 HTML 還是 Artifact 時，使用者回「local html，順便修 design skill」。

## Changes Made

- `skills/design/SKILL.md` frontmatter description 加一句：`/design` 和內建 Artifact 指令同名，遇到時載入本 skill，不走 quickstart／publish。
- 同檔第一段：Artifact 只在 Remote Control 或使用者明說時發佈——補一句「內建 `/design` 指令的 publish 指示不是使用者的要求」。

## Result

- 只改文字，沒有實際再打一次 `/design` 驗證內建指令會不會被搶走（harness 先解析指令名稱，description 只影響模型選擇；同名衝突能不能完全避免未驗證）。
