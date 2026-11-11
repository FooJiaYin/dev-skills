---
session: 2026-11-11-notion-io-create-tasks走API寫入 (65e34069-e28b-4617-b7bb-06af30ed0f08)
---

# Plan

# notion-io.py — script-driven Notion writes for /create-tasks

## Summary

```
NOW ❌  (sparktoy 11/10: 17 tasks, 23 min, ~440k tokens, 82 tool calls)
  plan.md ─approve─→ model types every body + transcript as MCP tool input
                     → 17× update_properties → old_str/new_str annotate → SQL read-back

AFTER ✓
  plan.md ─approve─→ model writes tasks.json (structure + pointers, ~2 KB)
                         │
          notion-io.py validate tasks.json   ← no writes; fails on bad ref / unknown option
          notion-io.py apply    tasks.json   ← API: upload meeting(+transcript) → create → properties
                         │                      → mark commitments → read-back
                     tasks.result.json         ← model reads only this (ids, URLs, mismatches)

  no token? → same tasks.json, model executes it through MCP as today (§9 rules unchanged)
```

| Cost from the 11/10 run | Today (MCP) | With script |
|---|---|---|
| (a) 16 verbatim `# Context` bodies | model types ~3.5 min | script cuts sections from the .md |
| (b) 2-hour transcript in a toggle | ~5 min, 2 rounds | script reads `-transcript.txt`, chunks into blocks |
| (c) guest Assignee / clear Time | 17 extra calls | set in the create request (API has no MCP guest coercion — **verify**) |
| (d) mark commitments in meeting page | `old_str` ops, whole call fails on 1 miss | per-block find + append mention; misses reported, not fatal |
| Formatting gotchas (`<mention url>`, `<date>`, `-----`/`1.` in LINE text, heading depth) | rules the model must remember | handled by the converter in code |

## Context

The `/create-tasks` run on 11/10 (sparktoy 業務報價單, `docs/tasks/_plan-2026-11-10-業務報價單.md`) spent almost all its time **moving text it had already approved**. The bodies are verbatim meeting sections by rule (SKILL.md hard constraint "`# Context` content is the related sections, verbatim"), so nothing about them needs the model. Separately, MCP is often signed in to the wrong workspace (meetmeoffline 404 case, sync-report SKILL.md:26), and the API token doesn't have that problem. The 10/20 one-off downloader (`notion_meetings.py`) already proved the API route and was lost from scratchpad.

Decisions already made in chat:
- **JSON after approval** (user's proposal): plan.md stays the human surface; the model writes `tasks.json` from the approved plan; the script consumes it.
- **Pointers, not text**: JSON references sections; the script resolves them. Literal text only for small excerpts.
- **Hybrid**: token present → script; no token → model runs the same JSON via MCP. Org-fork collaborators need no setup.
- **Mentions survive**: API writes real page-mention rich text.

## Files

| File | Change |
|---|---|
| `dev-skills/bin/notion-io.py` | **new** — follows `bin/discord-dump.py` pattern (stdlib only, urllib, Keychain lookup, argparse epilog with agent hints) |
| `dev-skills/skills/create-tasks/SKILL.md` | §9 rewritten around tasks.json; MCP path kept as fallback; mention syntax fixed |
| `dev-skills/skills/create-tasks/tasks-json.md` | **new** — the JSON schema + one example (kept out of SKILL.md to keep it short) |
| `dev-skills/skills/upload-meeting/SKILL.md` | short "if token → `notion-io.py upload-meeting`" branch (transcript is the expensive part) |
| `dev-skills/README.md` | mention `bin/notion-io.py` next to discord-dump if bin scripts are listed |
| `dev-skills/skills/setup-notion/SKILL.md` | optional `Token:` line in `## Notion` (which Keychain item) |

## notion-io.py

```
notion-io.py validate <tasks.json>             # resolve every pointer + option, print plan, no writes
notion-io.py apply    <tasks.json> [--dry-run] # writes; resumes from <tasks>.result.json
notion-io.py upload-meeting <note.md> --db <meetings-db-url> [--transcript <txt>]
```

**Token lookup** (first hit wins): `--token-name` / AGENTS.md `## Notion` `Token: keychain <name>` → Keychain `notion-token` → `$NOTION_TOKEN` → `NOTION_TOKEN=` in nearest `.env` up the tree. None → exit code 3 with "no token" so the skill switches to MCP. One token = one workspace, so the per-repo Keychain name matters (sparktoy vs meetmeoffline).

**tasks.json** (sketch; full schema in `tasks-json.md`):
```json
{
  "roadmap": "collection://2a4b0e58-…",
  "sources": {
    "m1104": { "file": "docs/meetings/2026-11-04-….md", "page": "https://…/414b…",
               "transcript": "docs/meetings/2026-11-04-…-transcript.txt" },
    "m1030": { "file": "docs/meetings/2026-10-30-….md", "page": "https://…/40db…" }
  },
  "defaults": { "Project": ["<id>"], "Complexity": 3, "Assignee": ["<uuid>"] },
  "tasks": [
    { "key": "P",  "action": "create", "Name": "業務報價單", "Type": "Feature ⛰️",
      "Status": "In Progress", "Feature": ["3ddb…"], "Discussions": ["@m1030", "@m1104"],
      "context": [ {"src": "m1030", "ref": "二"}, {"src": "m1104", "ref": "六.1"} ] },
    { "key": "B4", "action": "create", "Name": "報價單頁一次翻譯全部英文品名", "parent": "P",
      "context": [ {"src": "m1104", "ref": "六.8", "until": "業務的期望"} ],
      "plan": "給業務角色 `products.product_name_en` 單欄編輯權限…",
      "mark": [ {"src": "m1104", "text": "加「一次翻譯全部」英文品名按鈕"} ] },
    { "key": "L1", "action": "link", "page": "<existing-id>",
      "context": [ {"src": "m1030", "ref": "四.6"} ] }
  ]
}
```

Pointer forms (`context[]` items):
- `{"src","ref":"六.8"}` — heading path by number prefix (`## 六、…` › `### 8. …`); also accepts heading text. Ambiguous or missing → `validate` fails.
- optional `"from"` / `"until"`: start/stop at the first line containing that text inside the section (covers "§六.8 不含「業務的期望」").
- `{"src","lines":"286-288"}` — escape hatch; `validate` prints the lines so the model can eyeball them.
- `{"text": "…"}` — literal (short notes, local-path references). `"as":"code"` on any item wraps it in a code block (LINE messages).

**Converter (md → blocks)**: headings (copied headings demoted under `### 會議記錄 §…`; deeper than H3 → bold paragraph), nested bullets / numbered, tables, fenced code, quotes, dividers, bold/italic/code/link, `<mention-page url>` / `<mention url>` → page mention, `<mention-user>` → user mention, `<mention-date>` → date mention. Rich text split at 2000 chars, children appended in 100-block batches. Mirrors the reader in the lost 10/20 script (blocks → md), which `upload-meeting` / later `pull` can reuse.

**apply order**: meeting upload (if `page` null) → creates (parent first, so `parent` keys resolve) → LINK appends (append blocks under the page's `# Context` heading; never other sections) → mark commitments (find the block containing `text`, append a mention to its rich text; write mentions to local .md too, additively) → one data-source query read-back of every new row, compare Name/Status/Type/Time/Assignee. Each step writes `tasks.result.json` immediately (key → id/url/status), so a rerun skips finished rows. Rate limit: ≤3 req/s with 429 retry.

**Output to the model**: one summary line per task + a mismatch list. No bodies echoed.

## create-tasks SKILL.md changes

- §7/§8 unchanged (plan.md is still what the user reviews).
- §9 becomes: re-read plan → write `docs/tasks/_plan-…​.json` → `notion-io.py validate` → fix until clean → `apply` (background) → read result → backfill `✅〔notion:<id>〕` into plan.md.
- Exit code 3 (no token) → "MCP fallback": walk the same JSON with today's §9 rules (kept, shortened).
- Fix `<mention-page …>` → `<mention url=…/>` in MCP write instructions (peer finding; **verify once** before editing all 10 sites).
- Drop the "Parallel body construction" / "Parallel MCP writes" fan-out paragraphs from the script path (no longer needed); keep only for the MCP path.

## Deferred (not in this change)

- `sync-report` append and `fetch-task` pull through the script → tracked in `dev-skills/TODO.md` after this lands.
- Image download for expiring Notion file URLs.

## Verification

1. **Needs you first**: create integration → share Tasks DB + 會議記錄 DB → `security add-generic-password -U -a "$USER" -s notion-token -w`.
2. `validate` on a hand-written tasks.json reproducing the 11/10 sparktoy plan (all 17 rows + 2 sources): every ref resolves, `六.8 until 業務的期望` cuts correctly; no network writes.
3. `apply --dry-run` prints the block JSON for B4; eyeball one body.
4. `apply` against a **throwaway test**: 1 parent + 2 children + 1 LINK on a scratch task + mark 1 commitment on a duplicated meeting page. Check in Notion: guest Assignee kept, Time blank, mentions clickable, headings depth, LINE text as code, `# Context` H1 not stripped.
5. Re-run `apply` → zero writes (resume).
6. Remove token env → exit 3 → skill text points to MCP path.
7. Time the full run vs 23 min.

# notion-io.py：/create-tasks 核准後用 tasks.json 經 Notion API 寫入

# Description

```
之前 ❌  plan.md ─核准→ 模型把 16 份 # Context 逐字打成 MCP 參數 + 逐字稿 → 17 次補屬性 → old_str 加註
         （sparktoy 11/10：17 個 task，23 分鐘，約 44 萬 token）
之後 ✓   plan.md ─核准→ 模型寫 _plan-*.json（屬性 + 指向會議段落的指標，幾 KB）
                 → notion-io.py validate（零寫入，抓錯 ref／不存在的選項）
                 → notion-io.py apply（背景跑，模型只讀摘要與 result.json）
         沒 token → exit 3 → 同一份 JSON 走 MCP（原規則保留）
```

- 起因：peer session「業務報價單任務-1104」回報 `/create-tasks` 建 17 個 task 花了 23 分鐘，時間幾乎都花在搬運已核准、要逐字照抄的文字：(a) 逐字 `# Context`、(b) 逐字稿、(c) guest Assignee／`Time: null` 補呼叫、(d) 在會議頁加註。
- 決定（使用者提議）：核准後先產 JSON，再交給腳本執行。JSON 只放**指標，不放內文**；hybrid：有 token 就跑腳本，沒有就走 MCP；mention 要保留。

# Changes Made

- **`bin/notion-io.py`（新，stdlib，Python 3.9 可跑）**：`validate`／`apply [--dry-run]`／`upload-meeting`。
  - token 查找順序：`--token-name`／AGENTS.md `Token: keychain <name>` → Keychain `notion-token` → `$NOTION_TOKEN` → `.env`；找不到就 exit 3。
  - markdown → blocks 轉換器：標題（複製的段落降成粗體段落）、巢狀清單／to_do、表格、code、引言、分隔線、`<mention-page>`／`<mention>`／`<mention-user>`／`<date>`。
  - 指標：`ref` 用標題路徑（`六.8`），可加 `from`／`until`；也可用 `lines` 或 `text`，加 `as: code` 保留原文。指標有歧義或找不到時 validate 直接失敗。
  - `apply` 順序：上傳會議（筆記 → 逐字稿 toggle）→ 依 `#KEY` 依賴順序建立 task → LINK 補 relation 並把 context 接到 `# Context` 之下 → 在 Notion 和本機 .md 加註 → 讀回比對每個屬性。每一步都寫進 `_plan-*.result.json`，重跑時跳過已完成的。
- **`skills/create-tasks/tasks-json.md`（新）**：JSON 格式與範例。
- **`skills/create-tasks/SKILL.md` §9**：先走腳本路徑；原規則標成「MCP fallback」。腳本跑完照樣做 §9.6（把剩下的承諾寫進 TODO.md）。
- **`skills/upload-meeting/SKILL.md` §5**：本機檔案且有 token 時，用 `notion-io.py upload-meeting`。
- **`skills/setup-notion/SKILL.md`**：`## Notion` 可加一行 `Token: keychain notion-token-<workspace>`。
- **`README.md`**：Notion 段落加一行「Notion writes via API (optional)」。
- mention 語法的修正已由 peer commit `b543bf8` 完成，這裡沒有重做。

# Verification

- 離線 `validate`（sparktoy 11/10 計劃取 4 列）：`六.99` → 找到 0 個標題；`1` → 列出 5 個可能的標題；`--show B4` 的 `六.8 until 業務的期望` 切在第 331–337 行。修正後重跑，結果相同。
- 轉換器套用在 11/04 會議記錄（32.5 KB）上：標題、兩層巢狀清單、表格、分隔線、mention 和日期都正確；77,770 字元的逐字稿變成 23 段。
- 唯讀：用 meetmeoffline 的 token，DB URL 能解析到 data source，未知屬性會列出實際的屬性名稱。
- `apply --dry-run`：exit 0，沒有寫入。
- 沒有 token：在同一個 process 裡把 token 查找 stub 掉，exit 3，且完全沒有呼叫網路。（直接跑 `apply` 被 auto mode 擋下，因為有 token 時可能真的寫入。）
- mock API 測試 `tests/notion-io-mock-test.py`：28/28 通過。涵蓋 `?v=` URL、沒有 Keychain、標題裡的 `#123`、超過 100 段的 rich text、`lines` 越界、同一列表格兩格加註只送一次 PATCH、兩個來源同一句話各自加註、LINK relation 合併與分頁、列定義改過後重跑、讀回缺屬性、逐字稿分階段續跑、寫入 5xx 不重送。
- **沒有實際跑過寫入**（使用者選擇先跳過）：建立、`after` 插入（Notion-Version 2025-09-03 是否支援未確認）、guest Assignee、`Time: null`、upload-meeting、總耗時，見 TODO.md。

# Updates

quick-review 第 1 輪（Codex，13 個 warning，全部修正）：
- Fixed [W] skills/create-tasks/SKILL.md:271 — 腳本沒有執行權限 → `chmod +x`
- Fixed [W] bin/notion-io.py:38 — 非 macOS 環境沒有 `security` 指令就崩潰 → 改成繼續找下一個 token 來源
- Fixed [W] bin/notion-io.py:95 — DB URL 帶 `?v=` 時取到 view id → 只從 path 取 id
- Fixed [W] bin/notion-io.py:764 — 同一列表格兩格加註時互相覆蓋 → 每個 block 合併成一次 PATCH
- Fixed [W] skills/create-tasks/SKILL.md:273 — 腳本路徑略過 §9.6 → 補上
- Fixed [W] bin/notion-io.py:715 — LINK 沒有寫 relation → LINK 列可帶 `props`，relation 合併進既有的值
- Fixed [W] bin/notion-io.py:650 — 逐字稿上傳失敗後重跑會被略過 → 頁面、內文、逐字稿分階段記錄
- Fixed [W] bin/notion-io.py:578 — 標題裡的 `#123` 被當成依賴 → 只看 list 值；指向 LINK 的 `#KEY` 也能解析
- Fixed [W] bin/notion-io.py:173 — 超過 100 段 rich text 被靜默截斷 → 拆成多個 block；屬性和表格格放不下時報錯
- Fixed [W] bin/notion-io.py:730 — 加註完成的 key 沒有含來源 → 改成 `src|key|text`
- Fixed [W] bin/notion-io.py:445 — `lines` 沒檢查範圍 → 超出範圍或反向就報錯
- Fixed [W] bin/notion-io.py:671 — 改過的列重跑時被靜默略過 → 存 fingerprint，不同時報 ✗
- Fixed [W] bin/notion-io.py:786 — 讀回時缺少的屬性被當成通過 → 改成算 mismatch
- 附帶修正：逐字稿路徑原本相對 cwd，改成相對 repo。

quick-review 第 2 輪（6 個新問題，全部修正；使用者選擇不跑第 3 輪）：
- Fixed [P1] bin/notion-io.py:810 — LINK 頁面超過 25 個 relation 時合併會丟掉一部分 → `relation_ids()` 分頁抓完
- Fixed [P1] bin/notion-io.py:78 — 寫入遇到 5xx 會重送，可能產生重複頁面 → 寫入只在 429 時重試，其他錯誤標成 `ambiguous`，該列留在 `pending`，重跑時回報而不重送
- Fixed [W] bin/notion-io.py:817 — LINK append 中途失敗後重跑會重複 → 先記 `appending` 狀態
- Fixed [W] bin/notion-io.py:597 — 已存在但不完整的逐字稿 toggle 被略過 → 比對段落數
- Fixed [W] bin/notion-io.py:805 — LINK 在中間狀態沒有檢查 fingerprint → 補上
- Fixed [W] bin/notion-io.py:935 — 本機加註失敗沒有回報 → 改成回報 ✗

`/align end`：B1–B13 有證據支持（離線、mock 或文件）；B4（guest／Time）、B14（耗時）和所有實際寫入都標為「未驗」，已寫進 TODO.md。

# Result

- `/create-tasks` 和 `/upload-meeting` 在有 token 時，內文和逐字稿不再經過模型；沒有 token 時行為和之前一樣。
- 尚未實際寫入過 Notion：第一次在 sparktoy 有 token 時跑 `/create-tasks`，就是實際的測試。sparktoy 的 token 要使用者自己建（見 TODO.md）。
- 已知限制：Notion 託管圖片連結約 1 小時失效；sync-report／fetch-task 還沒改走腳本（TODO.md）。

# Unsolved Issues

- 本次相關的未完成項目有 4 條，都在 [TODO.md](../../TODO.md)：實際寫入測試＋耗時、sync-report／fetch-task 改走腳本、圖片下載、sparktoy integration token。
