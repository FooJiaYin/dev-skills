#!/usr/bin/env python3
"""Write to Notion through the official API, so page bodies never pass through the model.

    notion-io.py validate <tasks.json> [--show KEY]     resolve every pointer + property; no writes
    notion-io.py apply    <tasks.json> [--dry-run]      run it; resumes from <tasks>.result.json
    notion-io.py upload-meeting <note.md> --db <meetings DB/data source> --title T
                 [--props JSON] [--transcript FILE] [--page EXISTING]   (--page: append transcript only)

tasks.json format: skills/create-tasks/tasks-json.md.

Token (first hit): --token-name / `Token: keychain <name>` in the nearest AGENTS.md → Keychain
`notion-token` → $NOTION_TOKEN → NOTION_TOKEN= in the nearest .env. One token = one workspace; the
integration must be shared with every DB / page it touches (page ⋯ → Connections).
Exit codes: 0 ok · 1 some writes failed · 2 validation failed · 3 no token (use the MCP fallback).
"""
import argparse, copy, datetime, hashlib, json, os, re, subprocess, sys, time, urllib.error, urllib.request

API = "https://api.notion.com/v1"
VERSION = "2025-09-03"
HEX = re.compile(r"[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}", re.I)
TOKEN = None
_last = [0.0]


# ---------- token + http ----------

def walk_up(name, start="."):
    d = os.path.abspath(start)
    while True:
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
        if os.path.dirname(d) == d:
            return None
        d = os.path.dirname(d)


def keychain(name):
    try:
        r = subprocess.run(["security", "find-generic-password", "-s", name, "-w"], capture_output=True, text=True)
    except OSError:  # no macOS Keychain → fall through to $NOTION_TOKEN / .env
        return ""
    return r.stdout.strip()


def find_token(name=None, start="."):
    agents = walk_up("AGENTS.md", start)
    if not name and agents:
        m = re.search(r"Token:\s*keychain\s+`?([\w.-]+)", open(agents).read())
        name = m and m.group(1)
    tok = keychain(name) if name else ""
    tok = tok or keychain("notion-token") or os.environ.get("NOTION_TOKEN", "")
    env = walk_up(".env", start)
    if not tok and env:
        for line in open(env):
            m = re.match(r"\s*(?:export\s+)?NOTION_TOKEN\s*=\s*(.+)", line)
            if m:
                tok = m.group(1).strip().strip("'\"")
    return tok


class NotionError(Exception):
    ambiguous = False  # a write that may have been applied anyway — check before resending


def req(method, path, body=None):
    """GETs retry on 429/5xx/network errors; writes retry only on 429 (never applied). Any other
    write failure after sending may have landed, so it raises with `ambiguous` instead of resending."""
    write = method != "GET"
    for attempt in range(6):
        wait = 0.34 - (time.time() - _last[0])  # ~3 req/s
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        r = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                   headers={"Authorization": "Bearer " + TOKEN, "Notion-Version": VERSION,
                                            "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(r, timeout=60) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if attempt < 5 and (e.code == 429 or (not write and e.code in (500, 502, 503, 504))):
                time.sleep(float(e.headers.get("Retry-After") or 2 ** attempt))
                continue
            try:
                msg = json.load(e).get("message", "")
            except Exception:
                msg = ""
            hint = " (integration not shared with this page/DB, or wrong workspace token)" if e.code in (401, 403, 404) else ""
            err = NotionError(f"{method} {path}: HTTP {e.code} {msg}{hint}")
            err.ambiguous = write and e.code >= 500
            raise err
        except (urllib.error.URLError, OSError) as e:  # incl. read timeouts
            if attempt < 5 and not write:
                time.sleep(2 ** attempt)
                continue
            err = NotionError(f"{method} {path}: {e}" + (" — may have been applied; check before rerunning" if write else ""))
            err.ambiguous = write
            raise err


def nid(s):
    """Notion id from a URL / collection:// / bare id → dashed uuid. URLs: the path only —
    `?v=<view id>` and `#<block id>` are not the object."""
    s = s or ""
    if re.match(r"https?://", s):
        s = re.split(r"[?#]", s)[0]
    m = HEX.findall(s)
    if not m:
        raise NotionError(f"no Notion id in {s!r}")
    h = m[-1].replace("-", "").lower()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


def data_source(ref):
    """Accept a data source id/collection:// or a database URL; return (ds_id, properties schema)."""
    i = nid(ref)
    try:
        ds = req("GET", f"/data_sources/{i}")
    except NotionError:
        db = req("GET", f"/databases/{i}")
        ds = req("GET", f"/data_sources/{db['data_sources'][0]['id']}")
    return ds["id"], ds["properties"]


# ---------- markdown → blocks ----------

INLINE = re.compile(
    r'(?P<mpage><mention-page\s+url="(?P<mpu>[^"]+)"\s*(?:/>|>.*?</mention-page>))'
    r'|(?P<mgen><mention\s+url="(?P<mgu>[^"]+)"\s*(?:/>|>.*?</mention>))'
    r'|(?P<muser><mention-user\s+url="(?P<muu>[^"]+)"\s*(?:/>|>.*?</mention-user>))'
    r'|(?P<mdate><(?:mention-date|date)\s+start="(?P<mds>[^"]+)"(?:\s+end="(?P<mde>[^"]+)")?[^>]*?(?:/>|>.*?</(?:mention-date|date)>))'
    r'|(?P<bold>\*\*(?P<bt>.+?)\*\*)'
    r'|(?P<strike>~~(?P<st>.+?)~~)'
    r'|(?P<code>`(?P<ct>[^`]+)`)'
    r'|(?P<link>\[(?P<lt>[^\]]+)\]\((?P<lu>[^)\s]+)\))'
    r'|(?P<ital>(?<![\w*])\*(?!\s)(?P<it>[^*\n]+?)\*(?![\w*]))')


def _text(s, ann, link=None):
    out = []
    for i in range(0, len(s), 1900):
        t = {"type": "text", "text": {"content": s[i:i + 1900]}}
        if link and re.match(r"https?://", link):
            t["text"]["link"] = {"url": link}
        if ann:
            t["annotations"] = dict(ann)
        out.append(t)
    return out


def rich(s, ann=None):
    ann = ann or {}
    out, pos = [], 0
    for m in INLINE.finditer(s):
        if m.start() > pos:
            out += _text(s[pos:m.start()], ann)
        pos = m.end()
        if m.group("mpage") or m.group("mgen"):
            url = m.group("mpu") or m.group("mgu")
            try:
                out.append({"type": "mention", "mention": {"type": "page", "page": {"id": nid(url)}}})
            except NotionError:
                out += _text(m.group(0), ann)
        elif m.group("muser"):
            out.append({"type": "mention", "mention": {"type": "user", "user": {"id": nid(m.group("muu"))}}})
        elif m.group("mdate"):
            d = {"start": m.group("mds")}
            if m.group("mde"):
                d["end"] = m.group("mde")
            out.append({"type": "mention", "mention": {"type": "date", "date": d}})
        elif m.group("bold"):
            out += rich(m.group("bt"), dict(ann, bold=True))
        elif m.group("strike"):
            out += rich(m.group("st"), dict(ann, strikethrough=True))
        elif m.group("code"):
            out += _text(m.group("ct"), dict(ann, code=True))
        elif m.group("link"):
            out += _text(m.group("lt"), ann, m.group("lu"))
        elif m.group("ital"):
            out += rich(m.group("it"), dict(ann, italic=True))
    if pos < len(s):
        out += _text(s[pos:], ann)
    return out  # may exceed Notion's 100 items: append() splits blocks, fit() guards fields


def fit(rt, what):
    """A field that can't be split (property, table cell): keep ≤100 items, else fail loudly."""
    if len(rt) <= 100:
        return rt
    rt = rt[:99] + _text(plain(rt[99:]), {})
    if len(rt) > 100:
        raise NotionError(f"{what}: too much text for one Notion field")
    return rt


def block(kind, text="", **extra):
    b = {"object": "block", "type": kind, kind: {}}
    if kind not in ("divider", "table", "table_row"):
        b[kind]["rich_text"] = rich(text) if isinstance(text, str) else text
    b[kind].update(extra)
    return b


def code_block(text, lang="plain text"):
    return {"object": "block", "type": "code",
            "code": {"rich_text": _text(text, {}), "language": lang}}


def kids(b):
    return b[b["type"]].setdefault("children", [])


LIST = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(\[[ xX]\]\s+)?(.*)$")
SEP = re.compile(r"^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")


def md_blocks(md, headings=True):
    """Markdown → Notion blocks. headings=False turns every heading into a bold paragraph
    (used for sections copied under a task's `### 會議記錄` heading)."""
    lines = md.split("\n")
    out, stack, para, i = [], [], [], 0

    def flush():
        if para:
            out.append(block("paragraph", "\n".join(para)))
            para.clear()

    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if s.startswith("```"):
            flush(); stack.clear()
            lang, body = s[3:].strip() or "plain text", []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                body.append(lines[i]); i += 1
            out.append(code_block("\n".join(body), lang if lang in ("python", "javascript", "typescript", "json", "bash", "sql", "markdown", "html", "css", "yaml", "shell") else "plain text"))
            i += 1
            continue
        if not s:
            flush(); i += 1
            continue
        h = re.match(r"^(#{1,6})\s+(.*)$", s)
        if h:
            flush(); stack.clear()
            lvl = len(h.group(1))
            if headings and lvl <= 3:
                out.append(block(f"heading_{lvl}", h.group(2)))
            else:
                out.append(block("paragraph", rich(h.group(2), {"bold": True})))
            i += 1
            continue
        if re.match(r"^(-{3,}|\*{3,}|_{3,})$", s):
            flush(); stack.clear(); out.append(block("divider")); i += 1
            continue
        if s.startswith("|"):
            flush(); stack.clear()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i].strip()); i += 1
            header = len(rows) > 1 and SEP.match(rows[1])
            cells = [[c.strip() for c in re.split(r"(?<!\\)\|", r.strip("|"))] for r in rows if not SEP.match(r)]
            w = max(len(c) for c in cells)
            t = block("table", table_width=w, has_column_header=bool(header), has_row_header=False)
            kids(t).extend({"object": "block", "type": "table_row",
                            "table_row": {"cells": [fit(rich(c), "table cell") for c in r + [""] * (w - len(r))]}} for r in cells)
            out.append(t)
            continue
        if s.startswith(">"):
            flush(); stack.clear()
            q = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                q.append(lines[i].strip()[1:].strip()); i += 1
            out.append(block("quote", "\n".join(q)))
            continue
        m = LIST.match(line)
        if m:
            flush()
            ind = len(m.group(1).replace("\t", "    "))
            if m.group(3):
                b = block("to_do", m.group(4), checked=m.group(3).strip()[1] in "xX")
            else:
                b = block("bulleted_list_item" if m.group(2) in "-*+" else "numbered_list_item", m.group(4))
            while stack and stack[-1][0] >= ind:
                stack.pop()
            (kids(stack[-1][1]) if stack else out).append(b)
            stack.append((ind, b))
            i += 1
            continue
        if stack and line[:1] in (" ", "\t"):  # continuation under a list item
            kids(stack[-1][1]).append(block("paragraph", s)); i += 1
            continue
        stack.clear()
        para.append(s)
        i += 1
    flush()
    return out


def plain(rt):
    return "".join(t.get("plain_text") or t.get("text", {}).get("content", "") for t in rt)


# ---------- block writing ----------

def _leaf(b):
    return not b[b["type"]].get("children")


def split_long(blocks):
    """A block's rich_text holds ≤100 items: overflow continues in following sibling blocks."""
    out = []
    for b in blocks:
        t = b["type"]
        rt = b[t].get("rich_text") or []
        if len(rt) <= 100:
            out.append(b)
            continue
        b = copy.deepcopy(b)
        b[t]["rich_text"] = rt[:100]
        out.append(b)
        t2 = t if t in ("paragraph", "quote", "code") else "paragraph"
        for i in range(100, len(rt), 100):
            nb = {"object": "block", "type": t2, t2: {"rich_text": rt[i:i + 100]}}
            if t2 == "code":
                nb[t2]["language"] = b[t].get("language", "plain text")
            out.append(nb)
    return out


def append(parent, blocks, after=None):
    """Append blocks (any depth). Leaf children ride inline; deeper trees are appended per level."""
    created = []
    blocks = split_long(blocks)
    for n in range(0, len(blocks), 100):
        chunk, later = [], []
        for b in blocks[n:n + 100]:
            b = copy.deepcopy(b)
            ch = split_long(b[b["type"]].pop("children", []))
            if ch and all(_leaf(c) for c in ch):
                b[b["type"]]["children"], ch = ch[:100], ch[100:]
            elif b["type"] == "table":
                raise NotionError("table rows must be leaves")
            chunk.append(b); later.append(ch)
        body = {"children": chunk}
        if after:
            body["after"] = after
        res = req("PATCH", f"/blocks/{parent}/children", body)["results"]
        if after:  # with `after`, results are the parent's children; pick ours
            ids = [r["id"] for r in res]
            k = ids.index(after) + 1 if after in ids else 0
            res = res[k:k + len(chunk)]
        for r, ch in zip(res, later):
            if ch:
                append(r["id"], ch)
        created += res
        after = res[-1]["id"] if after and res else after
    return created


def children(bid):
    out, cur = [], None
    while True:
        r = req("GET", f"/blocks/{bid}/children?page_size=100" + (f"&start_cursor={cur}" if cur else ""))
        out += r["results"]
        if not r.get("has_more"):
            return out
        cur = r["next_cursor"]


def walk(bid):
    for b in children(bid):
        yield b
        if b.get("has_children") and b["type"] not in ("child_page", "child_database"):
            yield from walk(b["id"])


# ---------- properties ----------

def prop_value(name, schema, v, refs):
    if name not in schema:
        raise NotionError(f"unknown property {name!r} (have: {', '.join(schema)})")
    t = schema[name]["type"]
    if t in ("title", "rich_text"):
        return {t: fit(rich(v), name)}
    if t in ("select", "status"):
        if v is None:
            return {t: None}
        opts = [o["name"] for o in schema[name][t].get("options", [])]
        if opts and v not in opts:
            raise NotionError(f"{name}={v!r} is not an option ({' | '.join(opts)})")
        return {t: {"name": v}}
    if t == "multi_select":
        return {t: [{"name": x} for x in v]}
    if t == "people":
        return {t: [{"id": nid(x)} for x in v]}
    if t == "relation":
        return {t: [{"id": refs(x)} for x in v]}
    if t == "date":
        if v is None:
            return {t: None}
        return {t: {"start": v} if isinstance(v, str) else v}
    if t in ("number", "url", "checkbox", "email", "phone_number"):
        return {t: v}
    raise NotionError(f"property {name!r} of type {t} is not writable here")


def prop_read(p):
    t = p["type"]
    v = p[t]
    if t in ("title", "rich_text"):
        return plain(v)
    if t in ("select", "status"):
        return v and v["name"]
    if t == "multi_select":
        return sorted(x["name"] for x in v)
    if t in ("people", "relation"):
        return sorted(x["id"] for x in v)
    if t == "date":
        return v and (v["start"] if not v.get("end") else {"start": v["start"], "end": v["end"]})
    return v


def prop_expect(sent):
    t = next(k for k in sent if k != "type")
    v = sent[t]
    if t in ("title", "rich_text"):
        return plain(v)
    if t in ("select", "status"):
        return v and v["name"]
    if t == "multi_select":
        return sorted(x["name"] for x in v)
    if t in ("people", "relation"):
        return sorted(x["id"] for x in v)
    if t == "date":
        return v and (v["start"] if not v.get("end") else v)
    return v


# ---------- sources + pointers ----------

class Source:
    def __init__(self, key, spec, base):
        self.key, self.spec = key, spec
        self.path = os.path.join(base, spec["file"]) if spec.get("file") else None
        self.page = spec.get("page")
        self.label = spec.get("label", "會議記錄")
        self.transcript = os.path.join(base, spec["transcript"]) if spec.get("transcript") else None
        self.lines = open(self.path).read().split("\n") if self.path else []
        self.heads = [(n, len(m.group(1)), m.group(2).strip()) for n, l in enumerate(self.lines)
                      for m in [re.match(r"^(#{1,6})\s+(.*)$", l)] if m]
        if not self.page and self.lines and self.lines[0] == "---":
            fm = "\n".join(self.lines[1:self.lines.index("---", 1)])
            m = re.search(r"^\s*(?:page|url):\s*(\S+)", fm, re.M)
            self.page = m and m.group(1)

    def _span(self, idx):
        n, lvl, _ = self.heads[idx]
        end = next((h[0] for h in self.heads[idx + 1:] if h[1] <= lvl), len(self.lines))
        return n, end

    def section(self, ref):
        lo, hi = 0, len(self.lines)
        for part in str(ref).split("."):
            part = part.strip()
            cands = [k for k, h in enumerate(self.heads) if lo <= h[0] < hi and (lo == 0 or h[0] > lo)]
            def score(k):
                t = self.heads[k][2]
                if t == part:
                    return 3
                if t.startswith(part) and t[len(part):len(part) + 1] in ("、", ".", "．", ")", "）", " ", ":", "："):
                    return 2
                return 1 if part in t else 0
            best = max((score(k) for k in cands), default=0)
            hits = [k for k in cands if score(k) == best and best]
            if hits:
                top = min(self.heads[k][1] for k in hits)
                hits = [k for k in hits if self.heads[k][1] == top]
            if len(hits) != 1:
                raise NotionError(f"{self.key}: ref {ref!r} part {part!r} → {len(hits)} headings"
                                  + (": " + " / ".join(self.heads[k][2] for k in hits) if hits else ""))
            lo, hi = self._span(hits[0])
        return lo, hi

    def resolve(self, item):
        """→ (title, markdown, first_line, last_line) for one context pointer."""
        if "lines" in item:
            a, b = (int(x) for x in str(item["lines"]).split("-"))
            if not 1 <= a <= b <= len(self.lines):
                raise NotionError(f"{self.key}: lines {item['lines']} outside 1-{len(self.lines)} or reversed")
            return None, "\n".join(self.lines[a - 1:b]), a, b
        lo, hi = self.section(item["ref"])
        title = self.lines[lo].lstrip("#").strip()
        body = self.lines[lo + 1:hi]
        if item.get("from"):
            k = next((k for k, l in enumerate(body) if item["from"] in l), None)
            if k is None:
                raise NotionError(f"{self.key}: from {item['from']!r} not in §{item['ref']}")
            body = body[k:]
        if item.get("until"):
            k = next((k for k, l in enumerate(body) if item["until"] in l), None)
            if k is None:
                raise NotionError(f"{self.key}: until {item['until']!r} not in §{item['ref']}")
            body = body[:k]
        while body and not body[-1].strip():
            body.pop()
        return title, "\n".join(body), lo + 1, lo + 1 + len(body)


def item_blocks(src, item):
    """One pointer → blocks (heading as a bold paragraph, then the content)."""
    if "text" in item:
        return [code_block(item["text"])] if item.get("as") == "code" else md_blocks(item["text"], headings=False)
    title, md, _, _ = src.resolve(item)
    head = [block("paragraph", rich(title, {"bold": True}))] if title else []
    return head + ([code_block(md)] if item.get("as") == "code" else md_blocks(md, headings=False))


def body_blocks(items, sources, heading):
    """`# Context` / `# Plan`: group consecutive pointers by source under `## <mention>` + `### <label> §refs`."""
    if isinstance(items, str):
        items = [{"text": items}]
    out = [block("heading_1", heading)]
    k = 0
    while k < len(items):
        it = items[k]
        if "src" not in it:
            out += item_blocks(None, it); k += 1
            continue
        src, group = sources[it["src"]], []
        while k < len(items) and items[k].get("src") == it["src"]:
            group.append(items[k]); k += 1
        if src.page:
            out.append(block("heading_2", [{"type": "mention", "mention": {"type": "page", "page": {"id": nid(src.page)}}}]))
        refs = ", ".join("§" + str(g["ref"]) for g in group if "ref" in g)
        out.append(block("heading_3", f"{src.label} {refs}".strip()))
        for n, g in enumerate(group):
            if n:
                out.append(block("divider"))
            out += item_blocks(src, g)
    return out


# ---------- meeting upload ----------

def transcript_toggle(text):
    paras, cur = [], ""
    for line in text.split("\n"):
        if not line.strip():
            continue
        if cur and len(cur) + len(line) > 1800:
            paras.append(cur); cur = ""
        cur = (cur + "\n" + line) if cur else line
    if cur:
        paras.append(cur)
    t = block("heading_2", "逐字稿", is_toggleable=True)
    kids(t).extend(block("paragraph", _text(p, {})) for p in paras)
    return t


def strip_frontmatter(lines):
    if lines and lines[0] == "---" and "---" in lines[1:]:
        return lines[lines.index("---", 1) + 1:]
    return lines


def set_frontmatter(path, url):
    lines = open(path).read().split("\n")
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if lines and lines[0] == "---" and "---" in lines[1:]:
        end = lines.index("---", 1)
        fm = lines[1:end]
        if any(l.startswith("notion:") for l in fm):
            fm = [l for l in fm if not re.match(r"^\s+(page|last_synced):", l)]
            k = next(n for n, l in enumerate(fm) if l.startswith("notion:"))
            fm[k + 1:k + 1] = [f"  page: {url}", f"  last_synced: {stamp}"]
        else:
            fm += ["notion:", f"  page: {url}", f"  last_synced: {stamp}"]
        lines = ["---"] + fm + lines[end:]
    else:
        lines = ["---", "notion:", f"  page: {url}", f"  last_synced: {stamp}", "---", ""] + lines
    open(path, "w").write("\n".join(lines))


def create_meeting(path, db, title, props=None, on_page=None):
    """Create the page, record it (frontmatter + on_page) BEFORE writing the body, so a failed
    body append leaves a known partial page instead of a duplicate on rerun."""
    ds, schema = data_source(db)
    title_prop = next(k for k, v in schema.items() if v["type"] == "title")
    p = {title_prop: {"title": fit(rich(title), title_prop)}}
    for k, v in (props or {}).items():
        p[k] = prop_value(k, schema, v, nid)
    res = req("POST", "/pages", {"parent": {"type": "data_source_id", "data_source_id": ds}, "properties": p})
    set_frontmatter(path, res["url"])
    if on_page:
        on_page(res["url"])
    append(res["id"], md_blocks("\n".join(strip_frontmatter(open(path).read().split("\n")))))
    return res["url"]


def add_transcript(page, transcript, log=print):
    pid = nid(page)
    toggle = transcript_toggle(open(transcript).read())
    have = next((b for b in children(pid) if b["type"] == "heading_2" and plain(b["heading_2"]["rich_text"]) == "逐字稿"), None)
    if have:
        n, want = len(children(have["id"])), len(kids(toggle))
        if n < want:
            raise NotionError(f"{page}: 逐字稿 toggle is incomplete ({n}/{want} paragraphs) — delete it and rerun")
        log(f"skip: {page} already has a complete 逐字稿 toggle")
        return
    append(pid, [toggle])


def relation_ids(pid, prop):
    """All ids of a relation property — a page GET returns at most 25 (`has_more`)."""
    if not prop.get("has_more"):
        return [x["id"] for x in prop.get("relation", [])]
    out, cur = [], None
    while True:
        r = req("GET", f"/pages/{pid}/properties/{prop['id']}?page_size=100" + (f"&start_cursor={cur}" if cur else ""))
        out += [x["relation"]["id"] for x in r.get("results", [])]
        if not r.get("has_more"):
            return out
        cur = r["next_cursor"]


def upload_meeting(path, db, title, props=None, transcript=None, page=None, log=print):
    if not page:
        page = create_meeting(path, db, title, props)
    if transcript:
        add_transcript(page, transcript, log)
    log(f"uploaded: {page}")
    return page


# ---------- tasks.json ----------

def load(path):
    spec = json.load(open(path))
    base = spec.get("base") or os.path.dirname(os.path.abspath(path))
    while base != "/" and not os.path.isdir(os.path.join(base, "docs")):
        base = os.path.dirname(base)  # tasks.json lives in docs/tasks/; file paths are repo-relative
    sources = {k: Source(k, v, base) for k, v in spec.get("sources", {}).items()}
    return spec, sources


def deps(t, defaults):
    """'#KEY' items inside list (relation) values — not '#123' in a title."""
    props = dict(defaults or {}, **t.get("props", {}))
    return {x[1:] for v in props.values() if isinstance(v, list) for x in v if isinstance(x, str) and x.startswith("#")}


def order(tasks, defaults=None, known=()):
    """Creates that reference '#KEY' run after KEY; `known` = keys that need no create (LINK rows)."""
    done, out, pending = set(known), [], list(tasks)
    while pending:
        progressed = False
        for t in list(pending):
            if deps(t, defaults) <= done:
                out.append(t); done.add(t["key"]); pending.remove(t); progressed = True
        if not progressed:
            raise NotionError("circular #KEY references: " + ", ".join(t["key"] for t in pending))
    return out


def check(spec, sources, schema=None):
    errs, keys = [], [t.get("key") for t in spec["tasks"]]
    for k in set(keys):
        if keys.count(k) > 1:
            errs.append(f"duplicate key {k}")
    for t in spec["tasks"]:
        k = t.get("key")
        if t.get("action") not in ("create", "link"):
            errs.append(f"{k}: action must be create|link")
        if t.get("action") == "link" and not t.get("page"):
            errs.append(f"{k}: link needs page")
        for field in ("context", "plan"):
            items = t.get(field) or []
            for it in ([{"text": items}] if isinstance(items, str) else items):
                if "src" in it and it["src"] not in sources:
                    errs.append(f"{k}: unknown src {it['src']}")
                    continue
                if "src" in it and "text" not in it:
                    try:
                        sources[it["src"]].resolve(it)
                    except (NotionError, ValueError) as e:
                        errs.append(f"{k}: {e}")
        for mk in t.get("mark", []):
            src = sources.get(mk.get("src"))
            if not src:
                errs.append(f"{k}: mark has unknown src {mk.get('src')}")
            elif not src.page and not src.spec.get("upload"):
                errs.append(f"{k}: mark needs {src.key}.page or {src.key}.upload")
            elif src.lines and not any(mk["text"] in l for l in src.lines):
                errs.append(f"{k}: mark text not found in {src.path}: {mk['text'][:40]}")
        if schema is not None:
            props = dict(spec.get("defaults", {}), **t.get("props", {})) if t.get("action") == "create" else t.get("props", {})
            for name, v in props.items():
                try:
                    prop_value(name, schema, v, lambda x: "00000000-0000-0000-0000-000000000000")
                except NotionError as e:
                    errs.append(f"{k}: {e}")
    for t in spec["tasks"]:
        for d in deps(t, spec.get("defaults") if t.get("action") == "create" else None) - set(keys):
            errs.append(f"{t.get('key')}: #{d} is not a task key")
    try:
        order([t for t in spec["tasks"] if t.get("action") == "create"], spec.get("defaults"),
              [t["key"] for t in spec["tasks"] if t.get("action") == "link"])
    except NotionError as e:
        errs.append(str(e))
    return errs


def show(spec, sources, key):
    t = next(t for t in spec["tasks"] if t["key"] == key)
    for field in ("context", "plan"):
        items = t.get(field) or []
        for it in ([{"text": items}] if isinstance(items, str) else items):
            if "src" in it and "text" not in it:
                title, md, a, b = sources[it["src"]].resolve(it)
                print(f"--- {field} {it['src']} {it.get('ref', '')} lines {a}-{b} [{title or ''}]\n{md}")
            else:
                print(f"--- {field} text\n{it['text']}")


def apply(spec, sources, path, dry):
    rpath = re.sub(r"\.json$", "", path) + ".result.json"
    res = json.load(open(rpath)) if os.path.exists(rpath) else {"sources": {}, "tasks": {}, "marks": {}}
    save = lambda: dry or json.dump(res, open(rpath, "w"), ensure_ascii=False, indent=1)
    fails = []

    # 1. sources that still need a Notion page: page → body → transcript, each stage recorded
    for s in sources.values():
        r = res["sources"].get(s.key) or {}
        s.page = r.get("url") or s.page
        up = s.spec.get("upload")
        if not up:
            continue
        if r.get("status") in ("pending", "partial") or r.get("transcript") == "started":
            fails.append(f"source {s.key}: unfinished upload from an earlier run ({r.get('url') or 'page may exist in ' + up['db']}) "
                         f"— check it, then delete its entry in {rpath} to redo")
            continue
        try:
            if not s.page:
                if dry:
                    print(f"[dry] would upload {s.path}"); s.page = "00000000000000000000000000000000"; continue
                def record(url, s=s):
                    s.page = url
                    res["sources"][s.key] = {"url": url, "status": "partial"}; save()
                res["sources"][s.key] = {"status": "pending"}; save()
                create_meeting(s.path, up["db"], up["title"], up.get("props"), on_page=record)
                res["sources"][s.key]["status"] = "created"; save()
                print(f"uploaded {s.key}: {s.page}")
            r = res["sources"].get(s.key)
            if r and s.transcript and r.get("transcript") != "done" and not dry:
                r["transcript"] = "started"; save()
                add_transcript(s.page, s.transcript)
                r["transcript"] = "done"; save()
        except NotionError as e:
            if res["sources"].get(s.key, {}).get("status") == "pending" and not e.ambiguous:
                del res["sources"][s.key]; save()  # nothing was created
            fails.append(f"source {s.key}: {e}")

    ds, schema = data_source(spec["roadmap"])
    title_prop = next(k for k, v in schema.items() if v["type"] == "title")

    links = {t["key"]: t["page"] for t in spec["tasks"] if t["action"] == "link"}

    def refs(x):
        if x.startswith("#"):
            k = x[1:]
            if k in links:
                return nid(links[k])
            if k not in res["tasks"]:
                raise NotionError(f"#{k} was not created")
            return nid(res["tasks"][k]["id"])
        if x.startswith("@"):
            return nid(sources[x[1:]].page)
        return nid(x)

    def fp(t):
        d = dict(t, defaults=spec.get("defaults")) if t["action"] == "create" else t
        return hashlib.sha1(json.dumps(d, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]

    def changed(k, t, prev):
        if prev.get("fp") and prev["fp"] != fp(t):
            fails.append(f"{k}: definition changed since it was written ({prev.get('url')}) — fix the page by hand, "
                         f"or delete its entry in {rpath} to write it again")

    # 2. creates
    for t in order([t for t in spec["tasks"] if t["action"] == "create"], spec.get("defaults"), links):
        k, prev = t["key"], res["tasks"].get(t["key"], {})
        if prev.get("status") == "created":
            changed(k, t, prev)
            continue
        if prev.get("status") == "partial":
            fails.append(f"{k}: partial page {prev['url']} from an earlier run — check it, then delete its entry in {rpath} to recreate")
            continue
        if prev.get("status") == "pending":
            fails.append(f"{k}: an earlier create may have landed — search the Roadmap for it, then delete its entry in {rpath} to recreate")
            continue
        props = dict(spec.get("defaults", {}), **t.get("props", {}))
        try:
            sent = {name: prop_value(name, schema, v, refs) for name, v in props.items()}
            title_name = next((n for n in sent if schema[n]["type"] == "title"), None)
            if not title_name:
                raise NotionError(f"missing title property {title_prop!r}")
            blocks = body_blocks(t.get("context", []), sources, "Context")
            if t.get("plan"):
                blocks += body_blocks(t["plan"], sources, "Plan")
            if dry:
                print(f"[dry] create {k}: {props.get(title_prop)} · {len(blocks)} blocks")
                res["tasks"][k] = {"id": "00000000000000000000000000000000", "status": "created"}
                continue
            res["tasks"][k] = {"status": "pending", "fp": fp(t)}; save()
            page = req("POST", "/pages", {"parent": {"type": "data_source_id", "data_source_id": ds}, "properties": sent})
            res["tasks"][k] = {"id": page["id"], "url": page["url"], "status": "partial", "fp": fp(t),
                               "sent": {n: prop_expect(v) for n, v in sent.items()}}
            save()
            append(page["id"], blocks)
            res["tasks"][k]["status"] = "created"; save()
            print(f"created {k}: {page['url']}")
        except NotionError as e:
            if res["tasks"].get(k, {}).get("status") == "pending" and not e.ambiguous:
                del res["tasks"][k]; save()  # nothing was created
            fails.append(f"{k}: {e}")

    # 3. link rows: relations (merged into what's there) + context appended only under `# Context`
    for t in [t for t in spec["tasks"] if t["action"] == "link"]:
        k, prev = t["key"], res["tasks"].get(t["key"], {})
        if prev.get("status") == "linked":
            changed(k, t, prev)
            continue
        if prev.get("status") == "appending":
            fails.append(f"{k}: an earlier context append to {t['page']} stopped partway — check # Context, "
                         f"then set its status to \"linked\" (or delete the entry) in {rpath}")
            continue
        if prev.get("fp") and prev["fp"] != fp(t):
            changed(k, t, prev)
            continue
        try:
            pid = nid(t["page"])
            blocks = body_blocks(t.get("context", []), sources, "Context") if t.get("context") else []
            if dry:
                print(f"[dry] link {k}: props {list(t.get('props', {}))} · append {max(len(blocks) - 1, 0)} blocks under # Context"); continue
            if prev.get("status") != "props" and t.get("props"):
                have = req("GET", f"/pages/{pid}")["properties"]
                sent = {}
                for name, v in t["props"].items():
                    pv = prop_value(name, schema, v, refs)
                    if "relation" in pv:  # add, never drop existing relations
                        old = [{"id": x} for x in relation_ids(pid, have[name])] if name in have else []
                        pv["relation"] = old + [x for x in pv["relation"] if x["id"].replace("-", "") not in {o["id"].replace("-", "") for o in old}]
                    sent[name] = pv
                req("PATCH", f"/pages/{pid}", {"properties": sent})
                res["tasks"][k] = {"id": pid, "url": t["page"], "status": "props", "fp": fp(t)}; save()
            where = "no context"
            if blocks:
                top = children(pid)
                ctx = next((n for n, b in enumerate(top) if b["type"] == "heading_1" and plain(b["heading_1"]["rich_text"]).strip() == "Context"), None)
                res["tasks"][k] = {"id": pid, "url": t["page"], "status": "appending", "fp": fp(t)}; save()
                if ctx is None:
                    append(pid, blocks)
                    where = "page end (no # Context heading)"
                else:
                    end = next((n for n in range(ctx + 1, len(top)) if top[n]["type"] == "heading_1"), len(top))
                    append(pid, blocks[1:], after=top[end - 1]["id"])
                    where = "# Context"
            res["tasks"][k] = {"id": pid, "url": t["page"], "status": "linked", "fp": fp(t)}; save()
            print(f"linked {k}: {', '.join(t.get('props', {})) or 'no props'}; context → {where}")
        except NotionError as e:
            fails.append(f"{k}: {e}")

    # 4. mark commitments in the source pages (Notion + local .md, additive)
    by_src = {}
    for t in spec["tasks"]:
        for mk in t.get("mark", []):
            tid = res["tasks"].get(t["key"], {}).get("id")
            if tid and res["tasks"][t["key"]]["status"] in ("created", "linked"):
                by_src.setdefault(mk["src"], []).append((t["key"], mk["text"], tid, res["tasks"][t["key"]].get("url", "")))
    for sk, marks in by_src.items():
        mkey = lambda key, text: f"{sk}|{key}|{text}"
        todo = [m for m in marks if not res["marks"].get(mkey(m[0], m[1]))]
        if not todo:
            continue
        if dry:
            print(f"[dry] mark {len(todo)} commitment(s) in {sk}"); continue
        src = sources[sk]
        try:
            blocks = [b for b in walk(nid(src.page)) if b["type"] in ("paragraph", "bulleted_list_item", "numbered_list_item", "to_do", "table_row", "quote", "heading_3")]
        except NotionError as e:
            fails.append(f"mark {sk}: {e}"); continue
        edits = {}
        for key, text, tid, url in todo:
            needle = re.sub(r"\*\*|`", "", text)
            hits = []
            for b in blocks:
                if b["type"] == "table_row":
                    for ci, cell in enumerate(b["table_row"]["cells"]):
                        if needle in plain(cell):
                            hits.append((b, ci))
                elif needle in plain(b[b["type"]]["rich_text"]):
                    hits.append((b, None))
            if len(hits) != 1:
                fails.append(f"mark {key}: {len(hits)} blocks contain {needle[:40]!r} in {sk}"); continue
            b, ci = hits[0]
            rt = b["table_row"]["cells"][ci] if ci is not None else b[b["type"]]["rich_text"]
            if any(x.get("type") == "mention" and x["mention"].get("page", {}).get("id", "").replace("-", "") == tid.replace("-", "") for x in rt):
                res["marks"][mkey(key, text)] = "done"; continue
            # one PATCH per block: every cell of a table row edited together
            edits.setdefault(b["id"], (b, {}))[1].setdefault(ci, []).append((key, text, tid, url))
        for bid, (b, cells_items) in edits.items():
            def marked(rt, items):
                new = [clean_rt(x) for x in rt]
                for _, _, tid, _ in items:
                    new += [{"type": "text", "text": {"content": " "}}, {"type": "mention", "mention": {"type": "page", "page": {"id": tid}}}]
                return new
            items = [it for its in cells_items.values() for it in its]
            try:
                if b["type"] == "table_row":
                    cells = [marked(c, cells_items.get(n, [])) for n, c in enumerate(b["table_row"]["cells"])]
                    req("PATCH", f"/blocks/{bid}", {"table_row": {"cells": cells}})
                else:
                    req("PATCH", f"/blocks/{bid}", {b["type"]: {"rich_text": marked(b[b["type"]]["rich_text"], cells_items[None])}})
                for key, text, tid, url in items:
                    res["marks"][mkey(key, text)] = "done"
                    if src.path and not mark_local(src.path, text, url or f"https://www.notion.so/{tid.replace('-', '')}"):
                        fails.append(f"mark {key}: Notion marked, but {src.path} not — text missing or not unique there; add the mention by hand")
                save()
            except NotionError as e:
                fails.append(f"mark {items[0][0]}: {e}")
        print(f"marked {sum(1 for m in todo if res['marks'].get(mkey(m[0], m[1])))}/{len(todo)} in {sk}")

    # 5. read back every created page and compare the properties we sent
    if not dry:
        for k, r in res["tasks"].items():
            if r.get("status") != "created" or "sent" not in r or r.get("verified"):
                continue
            try:
                got = req("GET", f"/pages/{r['id']}")["properties"]
                bad = [f"{n}: sent {v!r} got " + (repr(prop_read(got[n])) if n in got else "no such property")
                       for n, v in r["sent"].items() if n not in got or prop_read(got[n]) != v]
                if bad:
                    fails.append(f"read-back {k}: " + "; ".join(bad))
                else:
                    r["verified"] = True
            except NotionError as e:
                fails.append(f"read-back {k}: {e}")
        save()

    n = {s: sum(1 for r in res["tasks"].values() if r.get("status") == s) for s in ("created", "linked")}
    print(f"done: {n['created']} created, {n['linked']} linked, {len(res['marks'])} marked, {len(fails)} problem(s) → {rpath}")
    for f in fails:
        print("  ✗ " + f)
    return 1 if fails else 0


def clean_rt(x):
    """Strip read-only fields so a fetched rich-text item can be written back."""
    t = x["type"]
    y = {"type": t, "annotations": x.get("annotations", {})}
    if t == "text":
        y["text"] = {"content": x["text"]["content"], "link": x["text"].get("link")}
    elif t == "mention":
        m = x["mention"]
        mt = m["type"]
        y["mention"] = {"type": mt, mt: {"id": m[mt]["id"]} if isinstance(m[mt], dict) and "id" in m[mt] else m[mt]}
    elif t == "equation":
        y["equation"] = x["equation"]
    return y


def mark_local(path, text, url):
    s = open(path).read()
    tag = f' <mention-page url="{url}"/>'
    i = s.find(text)
    if i < 0 or s.count(text) != 1:
        return False
    if not s[i + len(text):].startswith(tag):
        open(path, "w").write(s[:i + len(text)] + tag + s[i + len(text):])
    return True


# ---------- cli ----------

def main():
    global TOKEN
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0], epilog="Agents: run `apply` with run_in_background "
                                "(large bodies/transcripts take minutes). Read only the printed summary and the "
                                ".result.json — never echo page bodies back into the conversation.")
    p.add_argument("cmd", choices=["validate", "apply", "upload-meeting"])
    p.add_argument("file")
    p.add_argument("--show", help="validate: print the resolved sections for this task key")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--offline", action="store_true", help="validate without fetching the schema")
    p.add_argument("--token-name", help="Keychain service name holding the integration token")
    p.add_argument("--db"); p.add_argument("--title"); p.add_argument("--props"); p.add_argument("--transcript"); p.add_argument("--page")
    a = p.parse_args()
    start = os.path.dirname(os.path.abspath(a.file))
    TOKEN = find_token(a.token_name, start)
    need_net = not (a.cmd == "validate" and (a.offline or a.show))
    if need_net and not TOKEN:
        print("no Notion token (Keychain notion-token / $NOTION_TOKEN / .env) → use the MCP fallback.\n"
              "save one: security add-generic-password -U -a \"$USER\" -s notion-token -w", file=sys.stderr)
        sys.exit(3)
    try:
        if a.cmd == "upload-meeting":
            upload_meeting(a.file, a.db, a.title, json.loads(a.props) if a.props else None, a.transcript, a.page)
            return
        spec, sources = load(a.file)
        if a.cmd == "validate":
            if a.show:
                show(spec, sources, a.show); return
            schema = None if a.offline else data_source(spec["roadmap"])[1]
            errs = check(spec, sources, schema)
            for t in spec["tasks"]:
                refs = ", ".join(f"{i['src']}§{i.get('ref', i.get('lines', ''))}" for i in t.get("context", []) if isinstance(i, dict) and "src" in i)
                print(f"{t['key']:>4} {t['action']:<6} {t.get('props', {}).get('Name', t.get('page', ''))}  [{refs}]")
            for e in errs:
                print("  ✗ " + e)
            print(f"{len(spec['tasks'])} tasks, {len(errs)} error(s)" + (" (schema not checked)" if schema is None else ""))
            sys.exit(2 if errs else 0)
        errs = check(spec, sources)
        if errs:
            print("\n".join("  ✗ " + e for e in errs) + "\nrun validate first"); sys.exit(2)
        sys.exit(apply(spec, sources, a.file, a.dry_run))
    except NotionError as e:
        print(f"error: {e}", file=sys.stderr); sys.exit(1)


if __name__ == "__main__":
    main()
