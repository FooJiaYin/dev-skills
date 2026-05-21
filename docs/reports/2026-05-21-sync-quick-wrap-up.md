# /sync + /wrap-up Quick mode — Collaboration safety for git-illiterate partners

# Description

- A non-git-literate collaborator destroyed their local uncommitted work by typing destructive git commands after a failed `git pull` (suspected `git checkout .` or `git restore .` in panic). They also routinely open multiple Claude Code sessions against the same repo, creating index-race and silent file-overwrite risks. The fix wasn't to teach them git — it was to put their agent on the safety net by collapsing all git operations onto two skill entry points (`/sync` open, `/wrap-up` close) and forbidding destructive commands at the agent layer.
- Scope: single initiative with three architectural pivots (philosophy, helper splits, file structure).

### Goal

- Ship: (1) a new `/sync` start-of-day skill, (2) a Quick mode for `/wrap-up` tuned for partners who can't be trusted with popups, (3) shared commit-safety helper so Full + Quick stay aligned. Plus README updates so future agents discover the new flow.

# Design philosophy

## Discussion

- Started by listing what could go wrong at session start: (A) current session dirty/branch state, (B) remote drift (main moved, current branch moved, new teammate branches), (C) other sessions / worktrees. Enumerated ~21 case combinations.
- Pivot to **"mix > conflict"**: rather than worktree-isolating sessions (which leads to large merge conflicts at integration time that the partner can't resolve), aggressively merge everything together at sync time so conflicts surface early, small, and frequent. Worktree usage was explicitly deferred.
- Pivot to **agent-detected dirty classification**: rather than asking the user "are these changes yours?", the agent compares the dirty file list against files touched by this session's Edit/Write/Bash tool calls. Three cases (A: all from this session; B: mixed; C: none from this session) each route to `/wrap-up` Quick with mode-appropriate warnings.
- The conversation-context argument for routing dirty work to `/wrap-up` instead of auto-committing in `/sync`: only the original session has the chat history needed for a meaningful `/report` and commit message. `/sync` doing a generic WIP commit would produce garbage history.

## Decision

- **Chosen:** `/sync` does no commits; it routes dirty trees back to `/wrap-up` (Quick mode) by session-aware classification, then on clean trees auto-merges current-branch upstream + `origin/main` + teammate branches updated in last 24h. Any conflict aborts with a "contact reviewer" message.
- **Rationale:** Partner skill ceiling is low. Centralizing safety at the agent layer (popups, smart staging, abort-on-conflict) protects them without requiring them to learn git. The "mix > conflict" tradeoff accepts messier branch histories in exchange for surfacing integration friction early.
- **Trade-offs accepted:** Branch histories will be noisy (frequent merge commits). Auto-merging teammates' recent branches means a partner's PR could contain unrelated teammate work — the user (reviewer) accepts this for the simpler mental model. No worktree support.

# /wrap-up Quick mode

## Discussion

- Existing `/wrap-up` Full mode runs 9 interactive steps with multiple popups (Include report? Open PR? Push? Deploy?). Useless for the partner — they can't answer most of them.
- The cleanup step (Move → Gitignore → Delete) has three popups. Reduced to auto-delete-only-safe-cruft for Quick.
- `/verify`, `/code-review`, `/improve` skipped entirely in Quick — partner can't action their output.
- `/update-docs` runs propose-only via message-based control (no flag added to `/update-docs`); the propose markdown gets appended to `/report`'s output as a `# Suggested Doc Updates` section for the reviewer to act on later.
- Commit safety needed pre-commit safety (main-branch detection, MERGE_HEAD, oversize files), smart staging (session-aware, exclude sensitive/temp/other-session), commit message auto-generation with popup confirm, and push fallback on non-ff (switch to `wip/<ts>-<branch>`).

## Decision

- **Chosen:** Quick mode = 7 steps (scope-as-hint, update-docs propose-only, report with suggested docs, rename-session, commit+push with shared safety, optional Notion sync, deploy-detection-only). Popup budget: 1–2 (staging confirm + commit message confirm).
- **Rationale:** Strips ceremony to the minimum that still produces a useful report (the reviewer's view into what happened) and a safe commit (no leaked secrets, no force push, no main-branch contamination).
- **Trade-offs accepted:** Quick commits have generic `wip:` type and auto-generated message. Reviewer is expected to re-wrap-up in Full mode later for quality gates.

# Architecture pivots (3 rounds)

## Discussion

- **Round 1** — `/commit` as a third standalone skill that both `/sync` Phase 4 and `/wrap-up` Quick Step 7 invoke. Cleanly factored; small interface (single `--quick` context hint passed via message).
- **Round 2** — user flagged that `/sync` Phase 4 doesn't need staging logic (only push with non-ff fallback), so the `/commit`-from-sync invocation was overspecified. `/sync` Phase 4 became inline `git push` + non-ff fallback. `/commit` was now only used by one caller.
- **Round 3** — user pointed out single-caller `/commit` is overhead. Inlined `/commit` into `/wrap-up` Quick mode, deleted the standalone skill, updated AGENTS.md to remove `/commit` mention.
- **Round 4** — user asked about helper-file split for `/wrap-up` itself: SKILL.md (router) + full.md + quick.md, so Quick reader doesn't load Full's 130 lines of context (and vice versa). Adopted.
- **Round 5** — user spotted that Full mode's Step 7 (commit) and Quick mode's Step 7 share commit safety bullets but Full was missing them. Extracted shared bits to `commit.md`, referenced by both full.md and quick.md.
- **Round 6** — user pointed out that quick.md's table referenced "Full mode" steps ("see ./full.md for original steps"), which would defeat the split. Rewrote quick.md's table as standalone numbered steps (1–7, no Full reference).

## Decision

- **Chosen final layout:**
  ```
  ~/agent-skills/dev-skills/skills/
    sync/SKILL.md          93 lines
    wrap-up/
      SKILL.md             18 lines  — router (mode selection only)
      full.md             133 lines  — 9-step interactive flow
      quick.md             46 lines  — 7-step partner-safe flow
      commit.md            25 lines  — shared safety (pre-commit + staging + push fallback)
  ```
- **Rationale:** Each reader only loads relevant context. Shared commit safety lives in one place so adding a new sensitive pattern or push guard updates both modes. SKILL.md as a 18-line router is small enough to always load without polluting context.
- **Trade-offs accepted:** Three files inside `wrap-up/` instead of one. Closing 人話 message of Quick mode mentions "Full mode" as an instruction to the human reviewer (not a file reference) — that's intentional, not a leak.

# Updates

- **`/wrap-up` Full Step 7 push popup** (2026-05-21, post-Full-wrap-up): Replaced the binary "Open PR? Yes / No-stop" rule with a 3-option popup "Open PR / Push direct / Stop". Old rule forced direct-push solo-maintainer repos (like this one) into picking "Yes" (wrong) or "No-stop" (no push, requires manual follow-up). Now matches both PR-flow and direct-push repos without per-repo detection. Surfaced via `/improve` after I had to invent a third option mid-Full-wrap-up.
- **`/wrap-up` Full Step 9 strengthened** (2026-05-21, post-Full-wrap-up): Step 9 (`/improve`) is now explicitly **"always invoke, never skip"** even when earlier quality-gate steps were judged inapplicable. I had skipped `/improve` during this session's Full wrap-up (lumping it with skipped verify/code-review/deploy as "markdown-only"), which is wrong — `/improve` self-exits silently when no friction is detected, so the cost of always running is near zero and the value of catching friction is high. Saved `feedback_improve-always-run.md` user memory + index entry for cross-session reinforcement.

# Conclusion / Summary

- Shipped `/sync` skill (95 lines) + `/wrap-up` 4-file restructure (SKILL.md router + full.md + quick.md + commit.md) + README.md updates documenting the new flow. The dev-skills repo now models a four-phase development loop: **sync → discuss → implement → wrap-up**, with `/sync` and `/wrap-up` Quick designed specifically for collaborators who can't be trusted with raw git. Two post-wrap-up refinements landed via `/improve` (Step 7 push popup + Step 9 always-run).
- Open follow-ups:
  - `ibadminton-app/AGENTS.md` was also edited in this session (added `## Collaboration & Git Safety` section) but is in a different repo and scoped out of this wrap-up — needs separate commit.
  - SessionStart hook for auto-invoking `/sync` was discussed but deferred ("待人類確認需求後再加").
  - Cleanup of accumulating `wip/<timestamp>` branches is unhandled (deferred to a future helper skill).

# References

- `~/agent-skills/dev-skills/skills/sync/SKILL.md` (new)
- `~/agent-skills/dev-skills/skills/wrap-up/SKILL.md` (rewritten as router)
- `~/agent-skills/dev-skills/skills/wrap-up/full.md` (new)
- `~/agent-skills/dev-skills/skills/wrap-up/quick.md` (new)
- `~/agent-skills/dev-skills/skills/wrap-up/commit.md` (new)
- `~/agent-skills/dev-skills/README.md` (modified — added `/sync` to flow + tables)
- `ibadminton-app/AGENTS.md` (modified out-of-scope; separate commit needed)
- Plan file: appended below.

---

# Final Plan

# Plan — `/sync` skill + `/wrap-up` quick mode + AGENTS.md 防呆段

## Context

協作者完全沒有 git 概念，已發生過「直接 `git pull` 沒 stash 導致本地檔案被覆蓋」的災難（推測實際是 `git checkout .` 或 `git restore .` 在 pull 失敗後被誤用）。此外協作者會**同時開好幾個 Claude session 改同一個 repo**，會造成 git index race 和檔案系統 race。

對策不是教他 git，而是**讓他的 agent 當安全網**：把所有 git 動作收斂到兩個 skill 入口 — 開工 `/sync`、收工 `/wrap-up` — 中間禁止他 / agent 直接動 git 危險指令。

同時，現行 `/wrap-up` 全套要 10–30 分鐘，對「只是想存個檔下班」的場景太重；且其中 `/update-docs` 會要求協作者 approve doc 編輯，但他既看不懂內容、又會按 yes，等於污染 docs。所以需要 **Quick mode**：跳過 verify / code-review / deploy，把 `/update-docs` 降級為「在 report 裡列出 suggested doc updates」由真正的 reviewer（使用者本人）日後處理。

## 要改的檔案

### 1. NEW `~/agent-skills/dev-skills/skills/sync/SKILL.md`

開工儀式 skill。核心哲學：**dirty 找 wrap-up、乾淨就 auto-merge 一切**。混合不可怕、conflict 不會解才可怕。`/sync` 自己不 commit（那是 `/wrap-up` 的事），但只要工作樹乾淨就自動拉所有上游進來（main + 對方 branch），conflict 立刻 abort 並警告。

#### 核心算法

```
Phase 1: 處理未存改動（agent 自動判斷哪個 session 的）
  if 偵測到 dirty working tree:
    agent 比對:
      - dirty files = git status --short 列出的有改動檔案
      - session-edited files = 本 session 對話紀錄中 Edit/Write 動過的 files

    Case A — dirty files ⊆ session-edited files (這個 session 改的):
      AskUserQuestion popup (預設 = yes):
        「你在這個 session 改了 X 個檔案還沒存。要直接跑 /wrap-up Quick 收尾嗎？跑完會接著繼續 sync。」
        [yes] 跑 /wrap-up Quick (預設) → 跑完接著繼續 Phase 2
        [no]  先別 sync，我還在想  → 結束 /sync

    Case B — 部分 overlap (這個 session + 別的 session 混合):
      AskUserQuestion popup (預設 = yes):
        「工作樹有改動：
          - 這個 session 改的: <list>
          - 別處改的: <list>
         要直接在這裡跑 /wrap-up Quick 收尾全部（含別處的改動）嗎？
         注意：別處改動的 commit message + report 會比較生硬，因為這個 session 沒做過它們的對話 context。」
        [yes] 跑 /wrap-up Quick (預設) → 跑完接著繼續 Phase 2
        [no]  我要切回原 session 處理 → 結束 /sync

    Case C — 完全沒 overlap (純別的 session 改的):
      AskUserQuestion popup (預設 = yes):
        「工作樹有 X 個檔案改動，但這個 session 沒動過它們（可能是別的 session 留下的）。
         要直接在這裡跑 /wrap-up Quick 收尾嗎？
         注意：commit message + report 會比較生硬，因為這個 session 沒做過它們的對話 context。」
        [yes] 跑 /wrap-up Quick (預設) → 跑完接著繼續 Phase 2
        [no]  我要切回原 session 處理 → 結束 /sync

Phase 2: 抓最新狀態
  git fetch --all --prune

Phase 3: 拉所有上游進來（按順序試）
  3a. 當前 branch 落後 upstream:
      git pull --ff-only
      失敗 (diverged) → git merge @{u} --no-edit
  3b. origin/main 有當前 branch 沒有的 commit:
      git merge origin/main --no-edit       # auto-merge 進當前 branch
  3c. 對方近 24h 推的其他 feature branch (有當前 branch 沒有的 commit):
      for each such branch (按時間順序，最新先):
        git merge origin/<branch> --no-edit    # auto-merge，不 popup

  任何 merge 出現 conflict:
    git merge --abort                       # 完全還原
    停手，警告「Merge conflict 我不會解。你的工作已存在 <branch> 並 push。請聯絡 tech lead 處理」

Phase 4: 推回去
  git push
  失敗 (non-ff) → git switch -c wip/<YYYYMMDD-HHMM>-<branch> + git push -u origin HEAD

Phase 5: Ready report (人話)
  「✓ 同步完成
   你在 branch: <name>
   已併入: main (X 個 commit) + 對方的 <branches>
   工作目錄: 乾淨，可以開工」
```

#### 簡化掉的決策（全部寫死、不 popup）

- **Dirty 怎辦** → agent 自動判斷哪個 session 的，停手叫使用者去跑 /wrap-up（不嘗試自動 commit）
- **Main 有新 commit** → 自動 merge 進當前 branch，不問
- **對方推了新 branch** → 自動 merge 進當前 branch，不問（per user「都推薦 merge」）
- **不切 branch** → /sync 永遠停在當前 branch，不做「切到別人的 branch」這種事
- **不用 worktree** → 不偵測、不建議、不分隔（per user「他全部 mix 好過有 conflict 要解」）

#### Popup 場合

整個 /sync 只有**一種 popup**：Phase 1 偵測到 dirty 時，問「要跑 /wrap-up Quick 嗎？」（預設 yes，按 enter 自動繼續）。Case A/B/C 都會 popup，只是訊息內容不同（B/C 會多警告 commit message 會生硬）。其他決策全部 agent 自動做（dirty 判斷、merge 一律 auto）。conflict / detached HEAD / 缺 origin 這種「我不會處理」的狀況是訊息通知 + 結束流程，不是 popup。

#### Pre-flight check（仍然要做）

- `git status --short --branch`：dirty / branch / ahead-behind
- `git rev-parse --abbrev-ref HEAD`：當前 branch
- `<git-dir>/index.lock`：偵測是否另一個 session 正在動 git → 警告但不阻止
- `git rev-parse --git-common-dir` vs `git rev-parse --git-dir`：偵測 worktree（用於 lock file 路徑正確性，**不用於切 worktree**）
- Detached HEAD → 停手，「你在怪狀態，請聯絡 [reviewer]」
- 沒設 origin → 降級為 local-only，跳過 fetch/pull/push 全部步驟，純報告本機狀態
- `.git/REBASE_HEAD` / `.git/MERGE_HEAD` 等中斷狀態 → 停手，「你有未完成的 rebase / merge，請聯絡 [reviewer]」

#### Guardrails 禁止清單（agent 看到絕不執行）

- `git stash` 全家 (stash / pop / drop / clear) — 改用 WIP commit
- `git reset --hard` / `--mixed` 帶 path — 不可逆覆蓋
- `git checkout .` / `git restore .` / `git restore --staged .` — 不可逆丟改動（上次災難的指令）
- `git clean -fd` / `-fdx` — 不可逆刪 untracked
- `git push --force` / `-f` / `--force-with-lease` — 改寫遠端歷史
- `git rebase` interactive 或 onto main — 太複雜
- 在 main / master / develop 上 commit — 一律先 switch -c wip
- Auto-resolve merge conflict（編輯 conflict markers）— 99% 會錯
- `git merge --strategy ours` / `theirs` 自動丟掉一邊 — 等同手動覆蓋

#### 語氣

對所有狀態變化都用人話講，假設使用者完全不知道 fetch / pull / merge / branch / commit 是什麼。例如不講「fast-forward pull 完成」，講「拿到對方的最新進度」。

### 2. NEW `~/agent-skills/dev-skills/skills/commit/SKILL.md`

獨立的「safe commit + push」skill，**只負責 commit + push，不做 Notion sync**（/sync-report 由 caller 決定要不要跑）。`/wrap-up` Quick Step 7、`/sync` Phase 4 push、使用者單純想 commit 都呼叫它，邏輯一處。

#### 核心流程

```
Phase 1: Pre-commit safety
  - 在 main/master/develop 上 → git switch -c wip/<YYYYMMDD-HHMM>，告訴使用者
  - 偵測 dirty 中的 sensitive (.env*, *.pem, *_rsa, *secret*, *credential*, api*key*) → 排除 + 警告
  - 偵測 single file > 10MB → 排除 + 警告（疑似 binary）
  - 偵測 detached HEAD → 停手，請聯絡 reviewer
  - 偵測 .git/MERGE_HEAD / REBASE_HEAD → 停手，請聯絡 reviewer

Phase 2: Smart staging — session-aware classification
  agent 比對:
    - dirty files = git status --short
    - session-edited files = 本 session 對話紀錄中 Edit/Write/Bash 動過的 files

  分類每個 dirty file:
    a. session-edited + 非 sensitive + 非 temp → AUTO STAGE
    b. session-edited + sensitive → EXCLUDE + warn
    c. session-edited + temp-pattern (見下) → EXCLUDE + 告訴 user「不 stage 也不刪」
    d. NOT in session-edited → DEFER

  Temp file patterns (不 stage、不刪、留在 working tree):
    - agent scratchpads: findings.md, *-analysis.md, *-notes.md, PLAN.md (root)
    - log files: *.log, output.log, stderr.txt, test-output.*
    - screenshots / recordings: screenshot-*.*, recording-*.*
    - one-off scripts at root: *.py / *.ts / *.sh 在 repo root 且 git 未追蹤
    - 任何 untracked dir: tmp/, scratch/, playground/

  若有 (d) defer files → AskUserQuestion popup (multi-select):
    「以下檔案是 dirty 但這個 session 沒動過，要怎麼處理？」
    [預設勾選] (a) 一起 stage（我也要 commit 這些）
    [不勾]     (b) 跳過 — 留給其他 session 處理
    （per-file 勾選）

  列出最終 staged 清單給使用者（人話分類: 自動 stage / 跳過 sensitive / 跳過 temp / 使用者選擇）

Phase 3: Commit message (popup 確認)
  - 若 invocation context 提供 message hint → 用那個當預設
  - 否則 agent 從 diff + 對話 context 自動生成:
    ```
    <type>: <一行 summary>

    - <主要改動 bullet 1>
    - <主要改動 bullet 2>

    <若 diff > 25 files 或 > 2000 lines>
    ⚠️ LARGE DIFF — reviewer 建議拆分

    [<invocation source, e.g. Quick wrap-up by Claude Code>]
    session: <id>
    ```
  - 若 invocation context 表明是 Quick mode → type = "wip"
  - 否則跟隨 repo 既有 commit style（讀 `git log` 推測）

  AskUserQuestion popup (header: "Commit message"):
    [預設] Use as-is — 按 enter 直接用
    Edit  — 進 text input 改寫
    Cancel — 結束 /commit，已 stage 的維持 staged

Phase 4: Commit (確認後執行，無 popup)

Phase 5: Push
  - git push (新 branch 自動 -u origin HEAD)
  - 若 non-ff:
    git switch -c wip/<YYYYMMDD-HHMM>-<原branch>
    git push -u origin HEAD
    告訴使用者「原 branch 推不上去，已存到 wip/<ts>-<原branch>，請聯絡 reviewer」

Phase 6: Ready report
  「✓ 已 commit + push
   - branch: <name>
   - commit: <hash short> — <message first line>
   - push 到: origin/<branch>
   - 排除沒 commit 的: <list of sensitive / temp / deferred files>」
```

#### Invocation context patterns

- 直接被 user invoke (`/commit` 或 `/commit <message hint>`) → 標準流程，2 popups (defer files 若有 + commit message)
- 被 `/wrap-up` Quick Step 7 invoke → context 註明「Quick wrap-up」→ commit type 用 `wip`，其他同標準流程
- 被 `/sync` Phase 4 invoke → context 註明「sync auto-push」→ 跳過 Phase 1-3 (sync 後沒新改動可 commit)，只跑 Phase 5 push fallback

#### Popup 場合

- **Phase 2 defer files popup** — 只在有「非本 session 改的 dirty file」時才彈
- **Phase 3 commit message popup** — 一律彈（confirm / edit / cancel）

最少 1 popup（單純本 session 改動），最多 2 popups（有 deferred 檔案）。

#### Guardrails

- 永遠不 `git add -A`（用 smart staging）
- 永遠不 force push
- Sensitive files 一律排除（即使使用者要求 stage）
- Temp files 一律不 stage 也不刪（per user：「partner 常常留垃圾 temp file，可以不刪但不要 commit 上去」）
- 偵測異常狀態（detached / MERGE_HEAD）→ 停手
- **不做 Notion sync** — caller 決定要不要跑 /sync-report

### 3. MODIFY `~/agent-skills/dev-skills/skills/wrap-up/SKILL.md`

開頭新增 **Step 0: 選模式**：
- 若 invocation context 顯示「from /sync Quick auto-invoke」（不是 user 主動打 /wrap-up）→ 直接走 Quick mode，**跳過 popup**
- 否則 AskUserQuestion popup（header: "Wrap-up mode"）：
  - **Full**（預設，給使用者本人用）— 跑完整 9 步
  - **Quick**（給沒時間 / 沒 git 概念的協作者）— 只跑「給使用者看的 + 存檔」步驟

Quick mode 分支流程（依序）— **最少 1 popup（commit message confirm），有 deferred files 時最多 2**：

0. **Skip Step 0 (scope check)** — 完全跳。但若 `git diff --stat HEAD` > 25 files / 2000 lines，記下來，傳給 /commit 寫進 message
1. **Skip Step 1 (verify)** — partner 不會修失敗的 test，跑了浪費時間
2. **MODIFY Step 2 (update-docs)** → invoke `/update-docs` 時告訴它「Quick mode：只跑 Step 1–4 (Resolve scope → Detect layout → Classify diff → Propose)，**跳過 Step 5 (Edit)**，把 propose 的 markdown 輸出回傳給 /wrap-up 接著用」。**無 popup**（因為 propose 後不 confirm 就結束）
3. **Skip Step 3 (code-review)** — 最慢 + partner 無法 action，不寫 REVIEW.md
4. **KEEP Step 4 (/report)** 正常跑（接受內部偶發 popup — splits / target 都罕見）。完成後讀回 report 檔，**附加 `# Suggested Doc Updates` 章節**，內容為 step 2 dry-run 輸出 + 一行「執行 `/update-docs` 套用，或手動編輯」
5. **KEEP Step 5 (rename-session)** 正常跑
6. **MODIFY Step 6 (cleanup)** → **auto-delete-safe-only**，**無 popup**。只刪 `.DS_Store` / `*.swp` / `*~` / `.#*` / `*.orig`。其他 untracked（scratchpads / logs / screenshots）留著（/commit 會排除不 stage）
7. **MODIFY Step 7 (commit)** — invoke `/commit` skill（context 註明「Quick wrap-up」）。包含 1-2 popup（defer files 若有 + commit message confirm）。**不做 Notion sync**
8. **NEW Step 7.5 (Notion sync)** — 若有 Notion configured + step 4 產生了 report → invoke `/sync-report`。獨立步驟，不再被 /commit 包進去
9. **Partial Step 8 (deploy)** — 只跑 Branch A 偵測：若 CI handles，印一行 reminder 就結束。其他兩個 branch（manual deploy）整段跳
10. **Skip Step 9 (/improve)** — partner 無法 action 改進建議

**Quick mode 收尾訊息**：
```
✓ Quick wrap-up 完成
- branch: <name>
- commit: <hash short> — <message first line>
- 已 push 到 origin/<branch>
- report: docs/reports/<file>（含 # Suggested Doc Updates）
- 跳過: verify / code-review / deploy / improve
- 建議 reviewer 之後跑 /wrap-up Full 補上品質檢查
```

Step 7 完整邏輯（safety + staging + message + push fallback）已抽到 `/commit` skill — Quick mode Step 7 invoke `/commit` 並在 context 註明「Quick wrap-up」。詳見 Section 2 (NEW `/commit`)。

Full mode：原 Step 0–9 完全不動（Full 的 Step 7 維持原本 git add + popup 流程，不走 `/commit` — 因為 Full 是有經驗使用者用，互動 popup 是 feature 不是 bug）。

### 4. MODIFY `/Users/unilife/Downloads/dropout/ibadminton/ibadminton-app/AGENTS.md`

在現有 `## Layout` 段之後（line 30 附近）新增 `## Collaboration & Git Safety` 段。內容：

- **入口收斂**: 一律 `/sync` 開工、`/wrap-up` 收工（沒時間選 Quick mode）。中間想單純存檔可用 `/commit`（自動 safety + smart staging + push）。中間不要直接執行任何 git 指令。
- **協作哲學**: 永遠 commit + 盡量 merge。混合不可怕，conflict 不會解才可怕。
- **三段式 ritual**: dirty 時 `/sync` 不自動 commit，會請你去原 session 跑 `/wrap-up`（這樣 report 才寫得出來）。`/sync` 拉所有上游進來（main + 對方 branch），conflict 出現時聯絡 reviewer。
- **禁止清單**（agent 看到要立即停手 + 警告使用者）:
  - `git reset --hard` / `git checkout .` / `git restore .` / `git clean -fd` — 不可逆覆蓋
  - `git stash` 全家（drop / clear / pop） — 改用 WIP commit + push
  - `git push --force` / `git push -f` / `--force-with-lease` — 絕對不行
  - 在 `main` / `master` / `develop` 上 commit — 一律先 `git switch -c wip/<ts>`
  - `git rebase` — 太複雜，conflict 不會解
  - 自己編輯 conflict markers 嘗試解 merge — 99% 會錯
- **Conflict 一律停手**: 任何 merge / pull / push 出現 conflict → `git merge --abort` → 用人話告訴使用者「我不會解，請聯絡 [reviewer]，你的工作已存在 `<branch>` 並 push」→ 結束流程
- **Multi-session 警告（不阻止）**: 偵測到 `<git-dir>/index.lock` 或 uncommitted 改動跨 3+ 無關區域 → 提示「另一個 session 可能也在動」，但讓使用者自己判斷要不要繼續

寫成有號 list / 表格，agent 可掃讀。

## 執行順序

依賴關係：
- (2) `/commit` 是 (1) `/sync` Phase 4 和 (3) `/wrap-up` Quick Step 7 的 dependency

建議順序：
1. **先做 (2) `/commit`**（其他兩個依賴它）
2. 然後並行 (1) `/sync` + (3) `/wrap-up`
3. 最後做 (4) `ibadminton-app/AGENTS.md` 防呆段（提到所有 skill 名稱）

`/update-docs` 不改（per 新設計，message-based 控制，不需要 flag）

## 既有可重用 / 必須參照

- `/wrap-up` 既有的 Step 7 commit + push 邏輯（含 `/sync-report` 自動觸發、PR popup 等） — Quick mode 重用但跳過 PR popup
- `/report` 既有的 `# Updates` / `# Unsolved Issues` 段落位置慣例 — 新增 `# Suggested Doc Updates` 放在最後（Unsolved Issues 之後）
- `/update-docs` 既有的 step 1–4 邏輯 — Quick mode 透過 message 控制「只跑 step 1–4 不跑 step 5」，不需要改 /update-docs 本身
- **Message-based sub-skill 控制原則**：sub-skill 在同一個 agent context 跑，呼叫者用 invocation message 註明需求即可，不必為每種模式加 flag
- `AskUserQuestion` popup convention — `/wrap-up` 開頭 Full/Quick 選擇用 popup；`/sync` 全程不 popup（所有決策 agent 自動做 or 寫死規則）

## Out of scope（刻意不做）

- 不動 `/report` — 協作者不會直接跑 report，由 `/wrap-up` quick mode 代替；Quick mode 由 `/wrap-up` 負責附加 `# Suggested Doc Updates` 段
- 不動 root `CLAUDE.md` — `ibadminton-app/CLAUDE.md` 是 AGENTS.md 的 symlink（per 全域 convention）
- **`/sync` 不切 branch** — 永遠停在當前 branch、只做 merge。要切到別人的 branch 工作是 user 主動講的事，不是 `/sync` 的責任
- **`/sync` 不偵測 / 不建議 worktree** — per user decision「混合 > conflict」，全部 mix 進當前 branch 比物理隔離後解 conflict 安全
- **`/sync` 不解 conflict** — 任何 merge conflict 立即 abort + 警告聯絡 reviewer
- **`/sync` 不自動 commit** — 偵測到 dirty 就停手，把 commit + report 的責任丟回 `/wrap-up`（理由：/report 需要原 session 的對話 context 才寫得出有意義的報告）
- Full mode `/wrap-up` 不加 `# Suggested Doc Updates` — Full mode 已跑互動式 `/update-docs`，docs 已套用，再列建議多餘
- 不處理 `wip/<timestamp>` branch 的後續清理 — 累積太多再寫獨立 skill
- 不寫 SessionStart hook 自動跑 `/sync` — 待人類確認需求後再加（目前是 separate discussion）

## Verification

實作完成後：

1. **`/sync` smoke test**:
   - **乾淨樹 + 無上游更新**: 跑 `/sync` → fetch、無 merge，報告「狀態完美」
   - **乾淨樹 + main 有新 commit**: 跑 `/sync` → 自動 `git merge origin/main --no-edit` 進當前 branch、push，報告「已併入 main 的 X 個 commit」
   - **乾淨樹 + 當前 branch 落後 upstream**: 跑 `/sync` → `git pull --ff-only` 拉新
   - **乾淨樹 + 對方近 24h 推了 feat/Y**: 跑 `/sync` → 自動 `git merge origin/feat/Y --no-edit` 進當前 branch，無 popup
   - **Dirty (Case A — 本 session 改的)**: 跑 `/sync` → popup「要跑 /wrap-up Quick 嗎？」預設 yes → enter → 自動 invoke `/wrap-up` Quick → 跑完接著 Phase 2
   - **Dirty (Case B — 混合)**: 跑 `/sync` → popup 列出本 session 改的 vs 別處改的 + 警告 commit message 會生硬 → enter → 自動 invoke `/wrap-up` Quick 收尾全部 → 接著 Phase 2
   - **Dirty (Case C — 完全別 session)**: 跑 `/sync` → popup 警告本 session 沒做過這些改動 + commit message 會生硬 → enter → 自動 invoke `/wrap-up` Quick → 接著 Phase 2
   - **Merge main 出現 conflict**: 模擬 main 跟當前 branch 修同一行 → 跑 `/sync` → 應該 `git merge --abort` → 警告「Conflict 我不會解，請聯絡 [reviewer]」→ 結束
   - **Detached HEAD**: 跑 `/sync` → 立刻停手「你在怪狀態，請聯絡 [reviewer]」
   - **`<git-dir>/index.lock` 存在**: 跑 `/sync` → 警告「另一個 session 可能在動 git」
   - **沒設 origin**: 跑 `/sync` → 降級為 local-only，只報告本機狀態，不執行 fetch/pull/push

2. **`/commit` smoke test**:
   - 乾淨樹跑 `/commit` → 應該直接退出說「沒東西可 commit」
   - **本 session 改的 + 在 feature branch 跑 `/commit`** → auto-stage、彈 commit message popup confirm、enter → commit + push
   - **dirty + 在 main 上跑 `/commit`** → 自動 `git switch -c wip/<ts>` 再走流程，告訴使用者
   - **dirty 含 `.env.local`** → 不被 stage，警告
   - **dirty 含 10MB+ 檔案** → 不被 stage，警告
   - **dirty 含 temp file (findings.md / *.log / screenshot.png)** → 不 stage **也不刪**，告訴 user「temp 已保留但跳過 commit」
   - **dirty 含 不是本 session 改的檔案** → 彈 defer popup multi-select，user 勾選要不要一起 stage
   - **commit message popup edit** → user 選 Edit → text input → 用改後 message commit
   - **commit message popup cancel** → 結束 /commit，staged 維持 staged
   - Detached HEAD 跑 `/commit` → 停手請聯絡 reviewer
   - Push 被拒 (non-ff) → 自動 `git switch -c wip/<ts>-<branch>` + push 新 branch
   - 從 `/wrap-up` Quick invoke `/commit` (context 註明 Quick) → commit type 用 `wip`、message 結尾有 `[Quick wrap-up by Claude Code]` + session ID
   - **確認 /commit 不跑 /sync-report**（/sync-report 由 caller 跑）

3. **`/wrap-up` Quick mode smoke test**:
   - 跑 `/wrap-up` → 出現 Full / Quick popup
   - 選 Quick → 跳過 verify / code-review / deploy / improve；跑 /update-docs propose-only；跑 /report；附加 `# Suggested Doc Updates`；只刪 safe untracked；Step 7 invoke `/commit`（1-2 popup）；**Step 7.5 invoke /sync-report 如有 Notion**
   - 開啟 `docs/reports/YYYY-MM-DD-*.md` 確認最後有 `# Suggested Doc Updates` 段
   - 選 Full → 行為與現在完全一樣（不走 `/commit`）
   - 從 /sync Phase 1 invoke /wrap-up Quick → 不出現 Full/Quick popup（自動走 Quick）

4. **AGENTS.md**:
   - 開啟 `ibadminton-app/AGENTS.md`，確認 `## Collaboration & Git Safety` 段已插入正確位置（Layout 段後），內容包含禁止清單與 Multi-session 警告
   - 開新 Claude session 進 `ibadminton-app/`，問 agent「git pull」會否提示走 `/sync`
