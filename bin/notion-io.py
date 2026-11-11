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
import argparse, copy, datetime, json, os, re, subprocess, sys, time, urllib.error, urllib.request

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
    r = subprocess.run(["security", "find-generic-password", "-s", name, "-w"], capture_output=True, text=True)
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
    pass


def req(method, path, body=None):
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
            if e.code in (429, 500, 502, 503, 504) and attempt < 5:
                time.sleep(float(e.headers.get("Retry-After") or 2 ** attempt))
                continue
            try:
                msg = json.load(e).get("message", "")
            except Exception:
                msg = ""
            hint = " (integration not shared with this page/DB, or wrong workspace token)" if e.code in (401, 403, 404) else ""
            raise NotionError(f"{method} {path}: HTTP {e.code} {msg}{hint}")
        except urllib.error.URLError as e:
            if attempt < 5:
                time.sleep(2 ** attempt)
                continue
            raise NotionError(f"{method} {path}: {e}")


def nid(s):
    """Notion id from a URL / collection:// / bare id → dashed uuid."""
    m = HEX.findall(s or "")
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
    return out[:100]


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
                            "table_row": {"cells": [rich(c) for c in r + [""] * (w - len(r))]}} for r in cells)
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


def append(parent, blocks, after=None):
    """Append blocks (any depth). Leaf children ride inline; deeper trees are appended per level."""
    created = []
    for n in range(0, len(blocks), 100):
        chunk, later = [], []
        for b in blocks[n:n + 100]:
            b = copy.deepcopy(b)
            ch = b[b["type"]].pop("children", [])
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
    if t == "title":
        return {"title": rich(v)}
    if t == "rich_text":
        return {"rich_text": rich(v)}
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


def upload_meeting(path, db, title, props=None, transcript=None, page=None, log=print):
    if page:
        pid = nid(page)
        if any(b["type"] == "heading_2" and plain(b["heading_2"]["rich_text"]) == "逐字稿" for b in children(pid)):
            log(f"skip: {page} already has a 逐字稿 toggle")
            return page
    else:
        ds, schema = data_source(db)
        title_prop = next(k for k, v in schema.items() if v["type"] == "title")
        p = {title_prop: {"title": rich(title)}}
        for k, v in (props or {}).items():
            p[k] = prop_value(k, schema, v, nid)
        res = req("POST", "/pages", {"parent": {"type": "data_source_id", "data_source_id": ds}, "properties": p})
        pid, page = res["id"], res["url"]
        append(pid, md_blocks("\n".join(strip_frontmatter(open(path).read().split("\n")))))
        set_frontmatter(path, page)
    if transcript:
        append(pid, [transcript_toggle(open(transcript).read())])
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


def order(tasks):
    """Creates that reference '#KEY' run after KEY."""
    done, out, pending = set(), [], list(tasks)
    while pending:
        progressed = False
        for t in list(pending):
            deps = set(re.findall(r"#([\w.-]+)", json.dumps(t.get("props", {}))))
            if deps <= done | {x["key"] for x in tasks if x.get("action") != "create"}:
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
        if schema is not None and t.get("action") == "create":
            props = dict(spec.get("defaults", {}), **t.get("props", {}))
            for name, v in props.items():
                try:
                    prop_value(name, schema, v, lambda x: "00000000-0000-0000-0000-000000000000")
                except NotionError as e:
                    errs.append(f"{k}: {e}")
    try:
        order([t for t in spec["tasks"] if t.get("action") == "create"])
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

    # 1. sources that still need a Notion page
    for s in sources.values():
        s.page = res["sources"].get(s.key) or s.page
        up = s.spec.get("upload")
        if not s.page and up:
            if dry:
                print(f"[dry] would upload {s.path}"); s.page = "00000000000000000000000000000000"; continue
            s.page = upload_meeting(s.path, up["db"], up["title"], up.get("props"), s.spec.get("transcript"))
            res["sources"][s.key] = s.page; save()

    ds, schema = data_source(spec["roadmap"])
    title_prop = next(k for k, v in schema.items() if v["type"] == "title")

    def refs(x):
        if x.startswith("#"):
            return nid(res["tasks"][x[1:]]["id"])
        if x.startswith("@"):
            return nid(sources[x[1:]].page)
        return nid(x)

    # 2. creates
    for t in order([t for t in spec["tasks"] if t["action"] == "create"]):
        k, prev = t["key"], res["tasks"].get(t["key"], {})
        if prev.get("status") == "created":
            continue
        if prev.get("status") == "partial":
            fails.append(f"{k}: partial page {prev['url']} from an earlier run — check it, then delete its entry in {rpath} to recreate")
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
            page = req("POST", "/pages", {"parent": {"type": "data_source_id", "data_source_id": ds}, "properties": sent})
            res["tasks"][k] = {"id": page["id"], "url": page["url"], "status": "partial", "sent": {n: prop_expect(v) for n, v in sent.items()}}
            save()
            append(page["id"], blocks)
            res["tasks"][k]["status"] = "created"; save()
            print(f"created {k}: {page['url']}")
        except NotionError as e:
            fails.append(f"{k}: {e}")

    # 3. link appends — only under the existing `# Context`
    for t in [t for t in spec["tasks"] if t["action"] == "link"]:
        k = t["key"]
        if res["tasks"].get(k, {}).get("status") == "linked":
            continue
        try:
            pid = nid(t["page"])
            blocks = body_blocks(t.get("context", []), sources, "Context")
            top = children(pid) if not dry else []
            ctx = next((n for n, b in enumerate(top) if b["type"] == "heading_1" and plain(b["heading_1"]["rich_text"]).strip() == "Context"), None)
            if dry:
                print(f"[dry] link {k}: append {len(blocks) - 1} blocks under # Context"); continue
            if ctx is None:
                append(pid, blocks)
                where = "page end (no # Context heading)"
            else:
                end = next((n for n in range(ctx + 1, len(top)) if top[n]["type"] == "heading_1"), len(top))
                append(pid, blocks[1:], after=top[end - 1]["id"])
                where = "# Context"
            res["tasks"][k] = {"id": pid, "url": t["page"], "status": "linked"}; save()
            print(f"linked {k}: appended under {where}")
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
        todo = [m for m in marks if not res["marks"].get(f"{m[0]}|{m[1]}")]
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
                res["marks"][f"{key}|{text}"] = "done"; continue
            edits.setdefault((b["id"], ci), (b, []))[1].append((key, text, tid, url))
        for (bid, ci), (b, items) in edits.items():
            rt = b["table_row"]["cells"][ci] if ci is not None else b[b["type"]]["rich_text"]
            new = [clean_rt(x) for x in rt]
            for _, _, tid, _ in items:
                new += [{"type": "text", "text": {"content": " "}}, {"type": "mention", "mention": {"type": "page", "page": {"id": tid}}}]
            try:
                if ci is not None:
                    cells = [[clean_rt(x) for x in c] for c in b["table_row"]["cells"]]
                    cells[ci] = new
                    req("PATCH", f"/blocks/{bid}", {"table_row": {"cells": cells}})
                else:
                    req("PATCH", f"/blocks/{bid}", {b["type"]: {"rich_text": new}})
                for key, text, tid, url in items:
                    res["marks"][f"{key}|{text}"] = "done"
                    if src.path:
                        mark_local(src.path, text, url or f"https://www.notion.so/{tid.replace('-', '')}")
                save()
            except NotionError as e:
                fails.append(f"mark {items[0][0]}: {e}")
        print(f"marked {sum(1 for m in todo if res['marks'].get(f'{m[0]}|{m[1]}'))}/{len(todo)} in {sk}")

    # 5. read back every created page and compare the properties we sent
    if not dry:
        for k, r in res["tasks"].items():
            if r.get("status") != "created" or "sent" not in r or r.get("verified"):
                continue
            try:
                got = req("GET", f"/pages/{r['id']}")["properties"]
                bad = [f"{n}: sent {v!r} got {prop_read(got[n])!r}" for n, v in r["sent"].items() if n in got and prop_read(got[n]) != v]
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
    if i < 0 or s.count(text) != 1 or s[i + len(text):].startswith(tag):
        return
    open(path, "w").write(s[:i + len(text)] + tag + s[i + len(text):])


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
