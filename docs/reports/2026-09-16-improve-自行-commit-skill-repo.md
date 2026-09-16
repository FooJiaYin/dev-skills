# /improve 自行 commit skill repo

## 摘要

```
現在 ❌                                   改後 ✓
──────────────────────────────────────────────────────────────────────
/wrap-up Full                             /wrap-up Full
  step 7  commit ── 只有專案 repo            step 7  commit ── 只有專案 repo
  step 10 /improve ─ 改 skill，沒人 commit    step 10 /improve ─ 改完自己 commit skill repo

/wrap-up Quick                            （不變：guardrail 禁止跑 improve）
  guardrail 禁止 /improve ── 不會發生

手動 /improve                              手動 /improve
  「建議你跑 /wrap-up quick」                 歸戶 → 逐檔驗 hunk → 寫報告進 repo
  → 你跑了，但 cwd 是專案 repo ❌             → AskUserQuestion → commit + push ✓

報告位置                                   報告位置
  AGENTS.md 說寫 ~/agent-skills/docs/        寫進「改到的那個 git repo」
  但那裡不是 git repo，永遠 commit 不進去      → 報告與 skill 改動同一個 commit
  實務早就改寫 dev-skills/docs/ 了
```

# Description

`/improve` 改完 skill 檔後從來沒有一條路徑會把它 commit：Full mode 的 commit 在 step 7、improve 在 step 10；Quick mode 的 guardrail 直接禁止 improve；手動跑 improve 時它只「建議」跑 `/wrap-up quick`，而那會對著專案 repo 而不是 skill repo。結果是 dev-skills 長期躺著別的 session 留下的未 commit skill 改動（本次動手時有 7 個）。

順帶查證發現 `~/agent-skills/AGENTS.md` 的報告位置慣例已與實務相反：該處 26 份報告停在 2026-05-28，而 `dev-skills/docs/reports/` 有 11 份 git tracked、最新 2026-09-05。且 `~/agent-skills` 本身不是 git repo，寫在那裡的報告永遠無法版控。

# Changes Made

- `skills/improve/SKILL.md` — `## Wrap up` 從「建議跑 /wrap-up quick」改為 improve 自己的收尾步驟：依 `git rev-parse --show-toplevel` 歸戶 → 逐檔 `git diff` 確認 hunk 歸屬（此 repo 常有他人 leftovers）→ 報告寫進該 repo 的 `docs/reports/` → AskUserQuestion 確認 → 明確 pathspec commit + push。明文跳過 `/update-docs`、`rename-session`（會誤改專案 session 名）與 deploy 偵測。
- `skills/wrap-up/full.md` — step 10 註明 `/improve` 會自行 commit 它改到的 skill repo，step 7 不負責、也不要重複 commit。
- `~/agent-skills/AGENTS.md` — 報告位置慣例改為「寫進被改動檔案所屬的 git repo」，並說明 `~/agent-skills/` 不是 repo。

# Result

三個入口都有了通往 skill repo commit 的路徑。fork 同步依使用者選擇不自動跑，只印一行提醒累積筆數。

# Unsolved Issues

- `skills/wrap-up/SKILL.md` 結尾的 `## Common guardrails` 是空標題，未處理。
- 本次一併 commit 了先前 session 留下的 7 個 leftover 改動，依 skill 拆成 6 筆。`skills/wrap-up/full.md` 同時含 leftover（step 0 scope check）與本次（step 10）兩個 hunk，以 `hash-object` + `update-index` 拆進兩個 commit，未動工作樹。
