---
name: meeting-notes
description: Turn a meeting transcript into a structured Traditional-Chinese meeting note at docs/meetings/YYYY-MM-DD-<title>.md. Accepts multiple sources — a Plaud.ai share URL (web.plaud.ai/s/pub_…), a local .txt/.md transcript file, or transcript text pasted directly into chat. Use when the user says "整理成會議記錄", "做會議記錄", "/meeting-notes", "meeting notes from this transcript", or similar.
argument-hint: "<url | file-path | (paste transcript)>"
---

# meeting-notes — transcript → structured meeting notes

Three independent input modes. Detect which one applies, extract verbatim transcript, then run the **same** synthesis + write step. The synthesis step is identical regardless of source — only extraction differs.

## 1. Detect source

In priority order:

1. **URL** — argument starts with `http://` or `https://`. Branch by host:
   - `web.plaud.ai/s/pub_…` → §2A (Plaud)
   - Anything else → ask the user how to fetch it (most other transcription services are also auth-walled SPAs).
2. **File path** — argument resolves to an existing local file with `.txt`, `.md`, `.srt`, `.vtt`, or no extension. → §2B
3. **Pasted text** — argument (or recent user message) contains transcript-shaped text: timestamps (`HH:MM:SS`), speaker labels, or > 500 chars of dialog. → §2C
4. **Nothing usable** — ask via `AskUserQuestion`:
   - Paste transcript / file path / Plaud URL — let the user pick.

## 2. Extract transcript

### 2A. Plaud share URL

See [`sources/plaud.md`](sources/plaud.md) for the full extraction recipe (Playwright flow, tab switching, JSON decoding, cleanup, failure modes).

### 2B. Local file

```text
Read(file_path)
```

If the file is large (> ~25k tokens), `Read` will refuse — use `offset` + `limit` to page through.

Common formats:

- **`.txt` / `.md`** — usually already clean. Use as-is.
- **`.srt` / `.vtt`** — strip the sequence numbers and `-->` timing lines, keep the dialog. One pass with `sed` or Python.
- **No extension** — `file` command or just inspect the first 50 lines.

Pull metadata from the filename if it matches a date pattern (`YYYY-MM-DD-…`), otherwise extract from the file body (first few lines often have a title / date) or ask the user.

### 2C. Pasted text

The user already pasted it — it's in the conversation. Don't ask them to re-paste. Treat the most recent user message containing transcript-shaped text as the source.

If metadata (date, title, attendees) isn't in the paste, ask once via `AskUserQuestion`:

- Question: "需要補充哪些資訊？" with options Date / Title / Attendees / 都不用 (recommended if obvious from text).

## 3. Identify metadata

Regardless of source, you need:

- **Title** — if not provided, derive from main topic discussed in first 10% of transcript.
- **Date** — `YYYY-MM-DD`. If transcript spans midnight, use the start date.
- **Time** — `HH:MM` start time if available.
- **Duration** — explicit if provided (Plaud header), otherwise approximate from last timestamp.
- **Attendees** — distinct speaker labels. **Map `Speaker N` → real names whenever the transcript identifies them.** People introduce each other, get addressed by name, or sign off — sweep before defaulting to `Speaker N`. **Watch for homophone variants from transcription errors** — the same person may appear under multiple spellings (Chinese homophones, near-homophones, or auto-transcription artifacts). Pick the most-frequent spelling as canonical and collapse the rest.

## 3.5 Reconcile transcript noise

Auto-transcription 常把人名（同音字）、品牌（`LINE → 賴`、`Claude Code → 扣扣 / COCO / core code`、`Plaud → 拍檔`、`Cursor → 卡梭`）、framework 名（`Next.js → next 雞絲`）等聽錯，可能擴及整句。

1. **載入 glossary**：人名看 `AGENTS.md` / `CLAUDE.md` 的 `## Notion` → `### Team` 段；產品/工具/術語看 `## Glossary` 段或 `docs/meetings/glossary.md`。都沒有就跳過。
2. **修正**：依 glossary、上下文、常見錯誤模式做 best-guess 替換。
3. **存檔後**：把非顯然的替換條列印到 chat（**不寫進會議記錄**），並用 `AskUserQuestion` 問是否把這些對應加入 glossary，下次自動還原。

## 4. Synthesize the meeting note

Save **two** files to `docs/meetings/` (create the directory if missing). Title slug should be human-readable Traditional Chinese, not pinyin.

1. `docs/meetings/YYYY-MM-DD-<title>.md` — the synthesized meeting note (what this skill produces)
2. `docs/meetings/YYYY-MM-DD-<title>-transcript.<ext>` — the source transcript, preserved verbatim alongside the note

The transcript companion:

- **Plaud**：already handled by `sources/plaud.md` §4 — the cleaned transcript is written here directly.
- **Local file**：copy the original file to `docs/meetings/YYYY-MM-DD-<title>-transcript.<original-ext>`.
- **Pasted text**：write the pasted block to `docs/meetings/YYYY-MM-DD-<title>-transcript.txt`.

Use the following section structure. Section names are fixed; **drop a section entirely if it has no content** (do not write empty headings). The order must stay stable so different meetings stay comparable.

```markdown
# <YYYY/MM/DD> <會議標題>

## 一、會議基本資訊

- **日期**：YYYY-MM-DD HH:MM
- **時長**：約 N 小時 M 分
- **與會者**：<comma-separated real names and org>
- **資料來源**：<Plaud `pub_<uuid>` / 檔案 `path` / 對話貼上>

---

## 二、會議主題

<背景、為什麼開這場會、討論主軸、主要結論>

(用 bullets 而非段落。讀者只看這節就要知道整場會議發生什麼。)

---

## 三、<議題分組 1，例如「技術議題整理」>
<根據實際內容自由展開，可用 bullets、表格、對照式小標等任何能把這個議題講清楚的形式。不要硬塞固定欄位>

### 1. <子題> (optional)
…

## 四、<議題分組 2，例如「合作模式調整」>
…

---

## 五、會議結論

---

## 六、尚未定案事項

### 1. <領域> 待定
- <open question + why it's still open>

---

## Action Items

### @<姓名>
- <task> - <due（YYYY-MM-DD | 下週 | 4–6 月 | [TBD]）>

### @<姓名>
- <task> - <due>
```

## 5. Writing guidelines

**Before writing**: skim [`references/example.md`](references/example.md) to calibrate granularity, section structure, bold-label usage, and Action Items grouping. The example shows the shape — adapt it to the actual meeting; don't copy verbatim.

- **議題分組要分章**（§3、§4…），不要把所有議題塞在同一章下。
- **「已形成的共識」與「尚未定案」必須分開**。讀者要能一眼看出哪些決定了、哪些還在懸而未決。
- **未確認的事不要編造**：如果逐字稿沒指明截止日 / 沒指明某人姓名（只有 `Speaker 2`），照實寫 `[TBD]` 或 `Speaker 2（姓名未明）`。
- **每個議題內部的呈現方式不規範**——根據實際內容選最合適的形式。
- **Business tone.** 陳述精簡事實。
- **顆粒度要夠細，不要遺漏討論脈絡**。壓縮的是**說話的冗餘**（重複、口語贅字、跑題、閒聊），不是**討論的內容**。原則：
  - 每個被認真討論的點都該獨立成一條 bullet（或子 bullet），不要被合併掉，除非內容真的高度重複。
  - 推理鏈要保留：「為什麼有這個想法 → 對方怎麼回應 → 為什麼這樣決定」這條線不能斷
  - 具體例子、數字、案例（如「Google Cloud 一天噴 7000 元」「29 家店重做」「4 美元/月」）要留住——它們是判斷依據，不是裝飾
  - 邊角案例、附帶提到的 follow-up、被 parked 的想法都要記，不要因為「不是主軸」就丟掉
  - 一場 2 小時的會議，整理出來的議題分組通常會有 4–8 個子題、3–8 條 bullet。這是合理顆粒度的參考值
- **Synthesize the rambling, not the substance.** 「他說了 A，然後 B 補充說 C，然後又跑題講 D，回來又說 E」 → 整理成「A + C + E（三條 bullet）」，D 如果是雜訊就丟、如果有獨立價值就獨立一條。逐字引用只在 wording 本身重要時用。
- **Surface disagreements, not just decisions.** 兩人推不同方向、一邊贏了，**兩邊立場與贏的原因都要寫**。
- **條列式為主**。預設用 bullets / 巢狀 bullets 呈現，**不要寫成長段落**。每條 bullet 一個重點，需要展開就用子 bullet。段落只在 bullet 真的塞不下時用。
- **每個議題的呈現要服務內容，不要套版**。在 bullets 為主的前提下，可以從工具箱裡挑形式——**用哪個取決於這段討論長什麼樣，不要為了套樣式而硬塞**：
  - 議題有明確的問題-方案-分工三段 → 用 `- **核心問題**：…` / `- **解決方案**：…` / `- **分工**：…` 粗體小標
  - 兩人觀點對立，需要陳列出各自的立場
  - 議題討論完有洞見要 highlight，收斂成幾個重點共識
  - 多項並列比較 → 表格
- **不要灌水**。沒對立就別硬寫對照式；沒洞見就別硬下「管理判斷」；該議題就是平鋪直敘，就 bullets 寫完。樣式要從內容長出來，不是內容去配合樣式。
- **Open questions belong in 「尚未定案」**，不要藏在議題段裡裝作半個決定。
- **Action Items 必有 owner**；沒指明時段就寫 `[TBD]`，**絕不編造日期**。
- **Action Items 寫完後要回頭 sweep 整份逐字稿**——抓出所有「X 會處理 Y」「我來做 Z」「之後要 A」「下週前 B」這類承諾或任務指派，逐條核對都進了 Action Items。議題段裡順帶提到的承諾最容易被漏掉，**這次 sweep 不是 optional**。
- **不要灌水**。例如如果沒有「尚未定案」就刪掉那一章。

## 6. Offer Notion upload (optional)

After the file is saved, ask via `AskUserQuestion`:

- Question: "Upload to Notion Meetings DB?"
- Options:
  1. **Yes** — dispatch `/upload-meeting <saved-path>`. The new page URL is printed in chat.
  2. **No** (recommended when the user hasn't asked for upload) — skip; the local markdown is the only artifact.

The skill stays Notion-free by default: this prompt is the only Notion touchpoint. `/upload-meeting` itself handles missing config (it dispatches `/setup-notion` when `AGENTS.md` has no `## Notion` section), so don't pre-check config here.

## 7. Cleanup (ask first — never auto-delete)

The transcript is **preserved by design** in `docs/meetings/` (see §4). Do not delete it.

For intermediate working files (Plaud's raw dump, etc.), see the source recipe under `sources/`. Each source's cleanup step **must ask the user via `AskUserQuestion`** before deleting anything — never auto-cleanup. Local file / paste branches have no intermediates to clean.

## Failure modes & recovery

- **Read fails with "exceeds maximum allowed tokens"** — for local files, use `offset`/`limit`; for source-specific dumps, follow the cleanup step in the source recipe first.
- **Detected text doesn't actually look like a transcript** — bail out and ask the user, rather than fabricating a meeting note from an unrelated message.
- Source-specific failure modes live in each `sources/<source>.md` file.
