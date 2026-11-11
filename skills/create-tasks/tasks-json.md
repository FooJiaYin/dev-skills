# tasks.json — the approved plan, machine form

Written by the model after the user approves `_plan-*.md` (§9), saved next to it as `_plan-*.json`. `bin/notion-io.py` runs it with the API; without a token the model walks the same file through MCP. **Bodies are pointers, never pasted text** — the script copies sections from the local files.

```json
{
  "roadmap": "collection://<tasks data source id> | <Roadmap DB URL>",
  "sources": {
    "m1104": { "file": "docs/meetings/2026-11-04-<slug>.md",
               "page": "<meeting page URL — omit if the file has notion.page frontmatter>",
               "label": "會議記錄",
               "transcript": "docs/meetings/2026-11-04-<slug>-transcript.txt",
               "upload": { "db": "<Meetings DB URL>", "title": "<mention-date start=\"2026-11-04\"/> <topic>",
                           "props": { "Participants": ["<uuid>"] } } }
  },
  "defaults": { "Project": ["<page id>"], "Complexity": 3, "Status": "Not Started" },
  "tasks": [
    { "key": "P", "action": "create",
      "props": { "Name": "業務報價單", "Type": "Feature ⛰️", "Discussions": ["@m1104"] },
      "context": [ { "src": "m1104", "ref": "六.1" } ] },
    { "key": "B4", "action": "create",
      "props": { "Name": "報價單頁一次翻譯全部英文品名", "Feature": ["#P"], "Assignee": ["<uuid>"], "Time": null },
      "context": [ { "src": "m1104", "ref": "六.8", "until": "業務的期望" },
                   { "src": "line", "ref": "2026-11-05", "as": "code" },
                   { "text": "Unsolved：…" } ],
      "plan": "approved design text, or a list of pointers like context",
      "mark": [ { "src": "m1104", "text": "加「一次翻譯全部」英文品名按鈕" } ] },
    { "key": "L1", "action": "link", "page": "<existing task URL>",
      "props": { "Discussions": ["@m1104"] },
      "context": [ { "src": "m1104", "ref": "四.6" } ] }
  ]
}
```

- **`props`** — Notion property names as in the schema; `defaults` merge under every create. On a `link` row, relation values are added to what the page already has (give the source relation, e.g. `Discussions: ["@m1104"]`, so the meeting's Tasks relation mirrors it); `#KEY` relations are read only from list values. Values: title/text → string (inline md + `<mention-*>` ok) · select/status → exact option name · multi_select → list · people → list of user uuids (guests too — the API doesn't coerce them) · relation → list of ids/URLs, `#KEY` = a task created in this run, `@SRC` = a source page · date → `"YYYY-MM-DD"`, `{"start","end"}`, or `null` to keep it blank.
- **Pointers** (`context`, `plan`) — `ref` is a heading path by number or text (`六.8` = `## 六、…` › `### 8. …`); optional `from` / `until` cut at the first line containing that text; `lines: "286-288"` (file line numbers) is the escape hatch; `text` is literal markdown for short notes; `"as": "code"` keeps chat text (LINE `-----`, `1.`) literal. Consecutive pointers to one source render as `## <source mention>` + `### <label> §refs` + the sections (heading as bold, `---` between).
- **`mark`** — append a mention of the task after that text in the source page (and the local .md). The text must be unique in the page.
- **`upload`** — when the source has no page yet, the script creates it first (notes + `逐字稿` toggle from `transcript`) and writes `notion.page` into the .md.
- Results go to `_plan-*.result.json` (key → id, url, status). Re-running `apply` skips anything already done; a row edited after it was written, or a page left `partial`, is reported as `✗`, not rewritten.
