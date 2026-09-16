# wrap-up：deploy 前先對帳 schema、deploy 後要真的 fetch 過

```
現在❌                                    改後✓
──────────────────────────────           ──────────────────────────────
## 9. Deploy                              ## 9. Deploy
  Remember:                                 Remember:
  - 不確認不 deploy                          - 不確認不 deploy
  - CI/CD 就跳過                             - CI/CD 就跳過
  （沒有 schema 這件事）        ←缺           + Schema ships before code  ←新

  5. 印「Reminder: verify at <url>」          5. 必須 fetch 一個真的 render
     ↑ 提醒完就結束，沒人真的驗                  的頁面才能說「已部署」；
                                                200 不算證據（?_rsc= / HEAD /
                                                未登入 307 都會回 2xx-3xx）
```

# Description

- 來自 `sparktoy-erp` 的一次 prod 事故：程式碼 deploy 了、schema 沒跟上，`/pricing` 500 了三週沒人發現。事故本身見 `~/Downloads/dropout/sparktoy/sparktoy-erp/docs/reports/2026-09-16-prod-schema-落後八個migration-補救.md`。
- 本次把兩個可一般化的教訓寫回 `/wrap-up` 的 deploy 步驟，讓任何 repo 跑 `/wrap-up` Full 都不會再漏。

# Changes Made

- deploy 步驟的 `Remember:` 清單新增一條「schema 先於程式碼」
  `skills/wrap-up/full.md`

```md
- **Schema ships before code.** If the repo has a migrations dir, diff it against
  the target DB's applied-migrations table *before* deploying and apply what's
  pending. A stale schema fails at runtime, not at deploy time — the deploy
  "succeeds" and pages 500 days later.
```

- Branch C 的第 5 步從「印一句提醒」改成「必須實際 fetch 過」
  `skills/wrap-up/full.md`

```md
5. After a successful deploy, **fetch a real page before calling it deployed** —
   an authenticated GET that actually renders, not just the root URL. `200` alone
   proves nothing: RSC prefetches (`?_rsc=`), `HEAD`, and unauthenticated `307`s to
   a login page all return success without running the page's queries. Pair it with
   the platform's error log. Until that fetch is green, say "deployed, not yet verified".
```

Result: Success（兩處 grep 驗過仍在檔案上）。

# Updates

- 這兩條的來源是 `/improve` 的 F1 / F2。F3（harness classifier 擋下 `start-iap-tunnel` 與對 prod 跑 `yarn migrate`，使用者授權無法解除）判定為 repo-specific，寫進 `sparktoy-erp/AGENTS.md` 而非本 skill。
- F2 原本考慮寫進全域 `~/.claude/CLAUDE.md`，使用者選擇「skill 一句提醒」，因此落在 deploy 步驟旁邊 —— 宣告「已部署／正常」就發生在那一步。

# Result

- 只改 `skills/wrap-up/full.md`，兩個 hunk。
- ⚠️ 該檔案同時有**另一個 session 未提交的 hunk**（`## 0. Scope check` 那段），本次以 `git hash-object` + `update-index` 只暫存自己的兩個 hunk，不動對方的工作樹內容。
- repo 內另有 6 個檔案是其他 session 的未提交work（`create-tasks/`、`fetch-task/`、`rename-session/rename.sh`、`report/`、`sync-report/`、`wrap-up/commit.md`），未包含在本次 commit。
