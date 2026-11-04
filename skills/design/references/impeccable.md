# Using impeccable from design

design owns choosing directions, multiple versions and static HTML. impeccable owns refining and systematising code once a direction is set. Never route into impeccable's new-work, `live`, `generate` or `serve-question` — they need a server or a decision daemon and are slow. If impeccable isn't installed, do the step yourself and say so.

## How to call

- **Commands:** the Skill `impeccable:impeccable` with `<command> <target>`, e.g. `bolder the pricing section`. Name the target and what must stay untouched.
- **detect:** run the CLI directly. Resolve it from the installed skill, newest version: `~/.claude/plugins/cache/impeccable/impeccable/*/skills/impeccable/scripts/impeccable` (Claude) or `~/.codex/plugins/cache/impeccable/impeccable/*/skills/impeccable/scripts/impeccable` (Codex). Scan as URLs so the page renders — desktop, then phone:
  - `impeccable detect file:///abs/path.html` and `impeccable detect --viewport 390x844 file:///abs/path.html` (or the local dev URL).
  - Findings go to stderr — use `2>&1` or `--json`; `--quiet` prints only counts.
  - Exit 2 means findings were reported (not a failure); exit 1 means a target couldn't be scanned.
  - A bare file path scans source without rendering and misses most findings.

## What the user says → command

| User says | Command | Key rule |
|---|---|---|
| 「太平」「像別頁的弱版」「參考 radio 的寫法」 | `bolder` | Only the system's own moves, only the named target |
| 「空空的」「太擠」「不平衡」「要再分開一點」 | `layout` | Squint test, grouping, rhythm, density |
| 「太吵」「不要金漸層／框／icon」「不需要卡片」 | `quieter` / `distill` | Lower intensity / remove what doesn't belong |
| 「要呼吸感」「掀起」「搖晃」「stack 的感覺」 | `animate` | Motion explains state; one main moment |
| 「顏色不搭」「不要變成紫色」 | `colorize` | Keep brand colours |
| 「標題 serif 中文字體」「字太小」 | `typeset` | Type roles and scale |
| 「這句很廢」「這行怪」 | `clarify` | Copy only; ask before changing facts |
| 「手機要重新想，不是縮小」「會不會爆版」 | `adapt` | Rethink for touch and content priority, not scale. Overlap or overflow is a bug — fix it directly |
| 「卡頓」「優化 performance」 | `optimize` | Rendering and animation cost |
| 「要沒人想過網頁能做的效果」 | `overdrive` | One per page; propose 2–3 directions first (a Block mode option page counts as the proposal); never to hide weak basics |
| 「統一成元件」「規範」「UI library」 | `extract` → `document` | 3+ uses with the same intent; look-alikes with different jobs stay separate; migrate every use. With no design system it asks where to put it first |
| 「快好了」 | `polish` → `harden` | Finish details, then states and edge cases |
| The version the user leans to, before tuning | `critique` | Deep review of one version only (two isolated reviewers; costly) |

- While directions are still open, "更大膽／bolder" means deal a new batch of directions (design step 2, Direction page), not the `bolder` command — that command only refines a world that already shipped.
- Most feedback already carries its direction; the command's value is its diagnose-before-editing discipline.
