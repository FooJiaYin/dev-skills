# commit.md: detect main-direct workflow before forcing wip switch

- Date: 2026-05-25
- Scope: `skills/wrap-up/commit.md` — pre-commit safety rule

## 變更

`skills/wrap-up/commit.md` 的 "On main/master/develop → switch to wip" rule 改成有條件：先看 last 5 commits，若 ≥3 落在 main/master/develop（沒有從 feature branch merge 進來），視為 main-direct workflow，就地 commit；否則才開 wip branch。

## 動機

來自 biokey-web 專案 session 的 friction：該專案近期所有 commit 都直接落在 main，但 skill 預設行為會強制切 wip，導致每次 `/wrap-up` 都要靜默違反 skill 規則。新 fallback 讓 skill 自動辨識 main-direct workflow，不需要在每個 repo 加旗標。

## 影響檔案

- [skills/wrap-up/commit.md](../../skills/wrap-up/commit.md) — Pre-commit safety 區塊第一條

## 備註

- 偵測 heuristic：last 5 commits 計算「直接落在 main」（無 merge commit from feature branch）
- 沒改 quick.md / full.md，因為它們本來就引用 commit.md 規則
