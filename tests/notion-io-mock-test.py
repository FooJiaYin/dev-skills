"""Mocked-API checks for bin/notion-io.py (no network, no token). Run: python3 tests/notion-io-mock-test.py"""
import importlib.util, io, json, os, sys, tempfile, contextlib

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bin", "notion-io.py")

spec = importlib.util.spec_from_file_location("nio", SCRIPT)
nio = importlib.util.module_from_spec(spec); spec.loader.exec_module(nio)
ok = lambda c, m: print(("PASS " if c else "FAIL ") + m)

U = "1234567890abcdef1234567890abcdef"; V = "fedcba0987654321fedcba0987654321"
# WR-03
ok(nio.nid(f"https://www.notion.so/ws/{U}?v={V}").replace("-", "") == U, "WR-03 nid ignores ?v= view id")
ok(nio.nid(f"collection://{U[:8]}-{U[8:12]}-{U[12:16]}-{U[16:20]}-{U[20:]}").replace("-", "") == U, "WR-03 collection:// still works")
# WR-02
orig = nio.subprocess.run
nio.subprocess.run = lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError("security"))
os.environ["NOTION_TOKEN"] = "envtok"
ok(nio.find_token(None, tempfile.mkdtemp()) == "envtok", "WR-02 no Keychain → $NOTION_TOKEN")
nio.subprocess.run = orig; del os.environ["NOTION_TOKEN"]
# WR-08
t = [{"key": "A", "action": "create", "props": {"Name": "Fix #123 and #frontend"}},
     {"key": "B", "action": "create", "props": {"Feature": ["#A", "#L"]}}]
ok([x["key"] for x in nio.order(t, {}, ["L"])] == ["A", "B"], "WR-08 '#123' in title not a dep; #LINK key resolvable")
# WR-09
rt = nio.rich(" ".join(f"**b{i}** x" for i in range(120)))
ok(len(rt) > 100, f"WR-09 rich keeps all {len(rt)} items")
out = nio.split_long([nio.block("paragraph", rt)])
ok(len(out) == 3 and sum(len(b[b['type']]['rich_text']) for b in out) == len(rt), "WR-09 split_long → 3 blocks, nothing lost")
ok(len(nio.fit(rt, "cell")) <= 100 and nio.plain(nio.fit(rt, "cell")) == nio.plain(rt), "WR-09 fit keeps text in ≤100 items")
try:
    nio.fit(nio._text("x" * 400000, {}), "cell"); ok(False, "WR-09 fit raises on overflow")
except nio.NotionError:
    ok(True, "WR-09 fit raises on overflow")

# repo fixture
root = tempfile.mkdtemp(); os.makedirs(f"{root}/docs/tasks"); os.makedirs(f"{root}/docs/meetings")
open(f"{root}/docs/meetings/m.md", "w").write(
    f"---\nnotion:\n  page: https://www.notion.so/{V}\n---\n# M\n## 一、A\n- 做甲\n- 做乙\n| a | b |\n|---|---|\n| 做丙 | 做丁 |\n")
open(f"{root}/docs/meetings/n.md", "w").write("# N\n## 一、B\n- 做甲\n")
TPAGE = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"; NPAGE = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
plan = {"roadmap": f"collection://{U}",
        "sources": {"m": {"file": "docs/meetings/m.md"}, "n": {"file": "docs/meetings/n.md", "page": f"https://www.notion.so/{NPAGE}"}},
        "tasks": [{"key": "T1", "action": "create", "props": {"Name": "甲", "Discussions": ["@m"]},
                   "context": [{"src": "m", "ref": "一"}],
                   "mark": [{"src": "m", "text": "做甲"}, {"src": "n", "text": "做甲"}, {"src": "m", "text": "做丙"}]},
                  {"key": "T2", "action": "create", "props": {"Name": "丁"}, "mark": [{"src": "m", "text": "做丁"}]},
                  {"key": "L1", "action": "link", "page": f"https://www.notion.so/{TPAGE}", "props": {"Discussions": ["@m"]},
                   "context": [{"src": "m", "ref": "一"}]}]}
P = f"{root}/docs/tasks/_plan.json"; json.dump(plan, open(P, "w"), ensure_ascii=False)
spec_, sources = nio.load(P)
# WR-11
for bad in ("1-999", "5-3"):
    try:
        sources["m"].resolve({"lines": bad}); ok(False, f"WR-11 lines {bad} rejected")
    except nio.NotionError:
        ok(True, f"WR-11 lines {bad} rejected")

SCHEMA = {"Name": {"type": "title"}, "Discussions": {"type": "relation"}, "Status": {"type": "status", "status": {"options": [{"name": "Not Started"}]}}}
calls = []
row = {"id": "row1", "type": "table_row", "has_children": False,
       "table_row": {"cells": [[{"type": "text", "text": {"content": "做丙"}, "plain_text": "做丙"}],
                               [{"type": "text", "text": {"content": "做丁"}, "plain_text": "做丁"}]]}}
def para(i, s):
    return {"id": i, "type": "bulleted_list_item", "has_children": False,
            "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": s}, "plain_text": s}]}}
drop_prop = [False]
posted = {}
def fake(method, path, body=None):
    calls.append((method, path, body))
    if path.startswith("/data_sources/"):
        return {"id": U, "properties": SCHEMA}
    if method == "POST" and path == "/pages":
        n = sum(1 for c in calls if c[:2] == ("POST", "/pages"))
        posted[f"{n:032d}"] = {k: nio.prop_expect(vv) for k, vv in body["properties"].items()}
        return {"id": f"{n:032d}", "url": f"https://www.notion.so/new{n}"}
    if method == "GET" and path == f"/pages/{nio.nid(TPAGE)}":
        return {"properties": {"Discussions": {"type": "relation", "relation": [{"id": "old-rel"}]}}}
    if method == "GET" and path.startswith("/pages/"):
        props = {n: {"type": "title", "title": [{"plain_text": v}]} if n == "Name" else {"type": "relation", "relation": [{"id": x} for x in v]}
                 for n, v in posted[path.split("/")[2]].items()}
        if drop_prop[0]:
            props.pop("Discussions", None)
        return {"properties": props}
    if method == "GET" and "/children" in path:
        bid = path.split("/")[2]
        if bid == nio.nid(V):
            return {"results": [para("p1", "做甲"), para("p2", "做乙"), row], "has_more": False}
        if bid == nio.nid(NPAGE):
            return {"results": [para("q1", "做甲")], "has_more": False}
        return {"results": [{"id": "h", "type": "heading_1", "heading_1": {"rich_text": [{"plain_text": "Context"}]}}, para("c1", "x")], "has_more": False}
    if method == "PATCH" and path.endswith("/children"):
        return {"results": [{"id": f"new{i}"} for i in range(len(body["children"]))]}
    return {}
nio.req = fake
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = nio.apply(spec_, sources, P, False)
log = buf.getvalue()
res = json.load(open(P.replace(".json", ".result.json")))
row_patches = [c for c in calls if c[:2] == ("PATCH", "/blocks/row1")]
ok(len(row_patches) == 1 and all(any(x["type"] == "mention" for x in cell) for cell in row_patches[0][2]["table_row"]["cells"]),
   "WR-04 one PATCH for the table row, both cells marked")
ok(any(k.startswith("n|T1|") for k in res["marks"]) and any(k.startswith("m|T1|做甲") for k in res["marks"]), "WR-10 same text marked in both sources")
link_patch = [c for c in calls if c[:2] == ("PATCH", f"/pages/{nio.nid(TPAGE)}")]
ids = [x["id"] for x in link_patch[0][2]["properties"]["Discussions"]["relation"]] if link_patch else []
ok(ids[:1] == ["old-rel"] and len(ids) == 2, "WR-06 LINK relation merged with existing")
ok(res["tasks"]["L1"]["status"] == "linked" and rc == 0, f"apply rc={rc}, L1 linked\n{log}")
# WR-12
plan["tasks"][1]["props"]["Name"] = "丁 renamed"; json.dump(plan, open(P, "w"), ensure_ascii=False)
spec_, sources = nio.load(P)
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = nio.apply(spec_, sources, P, False)
ok(rc == 1 and "T2: definition changed" in buf.getvalue(), "WR-12 edited row reported on rerun")
# WR-13
r = json.load(open(P.replace(".json", ".result.json"))); r["tasks"]["T1"].pop("verified", None)
json.dump(r, open(P.replace(".json", ".result.json"), "w")); drop_prop[0] = True
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    nio.apply(spec_, sources, P, False)
ok("Discussions: sent" in buf.getvalue() and "no such property" in buf.getvalue(), "WR-13 missing property is a mismatch")

# WR-07: transcript stage separate
root2 = tempfile.mkdtemp(); os.makedirs(f"{root2}/docs/tasks"); os.makedirs(f"{root2}/docs/meetings")
open(f"{root2}/docs/meetings/u.md", "w").write("# U\n## 一\n- x\n")
open(f"{root2}/docs/meetings/u-t.txt", "w").write("line\n" * 10)
P2 = f"{root2}/docs/tasks/_p.json"
json.dump({"roadmap": f"collection://{U}", "sources": {"u": {"file": "docs/meetings/u.md", "transcript": "docs/meetings/u-t.txt",
           "upload": {"db": f"collection://{U}", "title": "U"}}}, "tasks": []}, open(P2, "w"))
fail_t = [True]
def fake2(method, path, body=None):
    if method == "PATCH" and path.endswith("/children") and body["children"][0].get("type") == "heading_2" and fail_t[0]:
        raise nio.NotionError("boom")
    return fake(method, path, body)
nio.req = fake2
s2, src2 = nio.load(P2)
with contextlib.redirect_stdout(io.StringIO()):
    rc1 = nio.apply(s2, src2, P2, False)
r2 = json.load(open(P2.replace(".json", ".result.json")))
ok(rc1 == 1 and r2["sources"]["u"]["status"] == "created" and r2["sources"]["u"]["transcript"] == "started", "WR-07 failed transcript recorded as started")
ok("notion:" in open(f"{root2}/docs/meetings/u.md").read(), "WR-07 frontmatter written")
fail_t[0] = False
s2, src2 = nio.load(P2)
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc2 = nio.apply(s2, src2, P2, False)
ok(rc2 == 1 and "unfinished upload" in buf.getvalue(), "WR-07 rerun reports the partial transcript instead of skipping it")

# ---- round 2 ----
import urllib.error
# CR-02: writes not retried on 5xx, flagged ambiguous; GETs retried
class FakeResp(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): pass
spec2 = importlib.util.spec_from_file_location("nio2", SCRIPT)
m2 = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(m2); m2.TOKEN = "x"; m2.time.sleep = lambda s: None
hits = []
def fake_open(r, timeout=60):
    hits.append(r.get_method())
    if len(hits) == 1 or r.get_method() != "GET":
        raise urllib.error.HTTPError(r.full_url, 502, "bad", {}, io.BytesIO(b"{}"))
    return FakeResp(b'{"ok": 1}')
m2.urllib.request.urlopen = fake_open
ok(m2.req("GET", "/x") == {"ok": 1} and hits == ["GET", "GET"], "CR-02 GET retried on 502")
hits.clear()
try:
    m2.req("POST", "/pages", {}); ok(False, "CR-02 POST 502 not retried")
except m2.NotionError as e:
    ok(hits == ["POST"] and e.ambiguous, "CR-02 POST 502 not retried, flagged ambiguous")
# CR-01: relation pagination
pages = iter([{"results": [{"relation": {"id": "r1"}}], "has_more": True, "next_cursor": "c"},
              {"results": [{"relation": {"id": "r2"}}], "has_more": False}])
m2.req = lambda *a, **k: next(pages)
ok(m2.relation_ids("p", {"id": "pid", "has_more": True, "relation": [{"id": "r1"}]}) == ["r1", "r2"], "CR-01 relation ids paginated")
# WR-02: incomplete toggle detected
tdir = tempfile.mkdtemp(); tf = f"{tdir}/t.txt"; open(tf, "w").write(("x" * 1000 + "\n") * 10)
def fk(method, path, body=None):
    if path.startswith(f"/blocks/{m2.nid(V)}/children"):
        return {"results": [{"id": "tg", "type": "heading_2", "heading_2": {"rich_text": [{"plain_text": "逐字稿"}]}}], "has_more": False}
    if path.startswith("/blocks/tg/children"):
        return {"results": [{"id": "a"}], "has_more": False}
    raise AssertionError(path)
m2.req = fk
try:
    m2.add_transcript(f"https://www.notion.so/{V}", tf); ok(False, "WR-02 incomplete toggle reported")
except m2.NotionError as e:
    ok("incomplete" in str(e), "WR-02 incomplete toggle reported")
# WR-04: mark_local returns False when ambiguous
lf = f"{tdir}/l.md"; open(lf, "w").write("做甲 and 做甲\n")
ok(m2.mark_local(lf, "做甲", "u") is False, "WR-04 ambiguous local mark reported")
# WR-03 / WR-01: link rows in intermediate states
P3 = f"{root}/docs/tasks/_plan3.json"
plan3 = {"roadmap": f"collection://{U}", "sources": plan["sources"],
         "tasks": [{"key": "L1", "action": "link", "page": f"https://www.notion.so/{TPAGE}", "props": {"Discussions": ["@m"]}},
                   {"key": "L2", "action": "link", "page": f"https://www.notion.so/{TPAGE}", "context": [{"src": "m", "ref": "一"}]}]}
json.dump(plan3, open(P3, "w"), ensure_ascii=False)
json.dump({"sources": {}, "marks": {}, "tasks": {"L1": {"status": "props", "fp": "stale"}, "L2": {"status": "appending", "fp": "x"}}},
          open(P3.replace(".json", ".result.json"), "w"))
nio.req = fake; calls.clear()
s3, src3 = nio.load(P3)
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    nio.apply(s3, src3, P3, False)
o = buf.getvalue()
ok("L1: definition changed" in o and not any(c[0] == "PATCH" for c in calls), "WR-03 changed LINK in props state stops, no write")
ok("L2: an earlier context append" in o, "WR-01 partial LINK append reported, not re-appended")
# CR-02 in apply: non-ambiguous create failure leaves no pending entry
P4 = f"{root}/docs/tasks/_plan4.json"
json.dump({"roadmap": f"collection://{U}", "sources": {}, "tasks": [{"key": "Z", "action": "create", "props": {"Name": "z"}}]}, open(P4, "w"))
def fake4(method, path, body=None):
    if method == "POST":
        e = nio.NotionError("HTTP 400"); raise e
    return fake(method, path, body)
nio.req = fake4
s4, src4 = nio.load(P4)
with contextlib.redirect_stdout(io.StringIO()):
    nio.apply(s4, src4, P4, False)
ok("Z" not in json.load(open(P4.replace(".json", ".result.json")))["tasks"], "CR-02 clear 4xx failure leaves no pending entry")
def fake5(method, path, body=None):
    if method == "POST":
        e = nio.NotionError("HTTP 502"); e.ambiguous = True; raise e
    return fake(method, path, body)
nio.req = fake5
with contextlib.redirect_stdout(io.StringIO()):
    nio.apply(s4, src4, P4, False)
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    nio.apply(s4, src4, P4, False)
ok("may have landed" in buf.getvalue(), "CR-02 ambiguous create stays pending and is reported on rerun")
