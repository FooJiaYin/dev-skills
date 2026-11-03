#!/usr/bin/env python3
"""Dump one Discord channel (+ all its threads) to a readable markdown file via the bot API.

    discord-dump.py <channel_id> <out.md> [--after YYYY-MM-DD]

Token: Keychain `discord-bot-token`, else $DISCORD_BOT_TOKEN. The bot must be in the guild
and able to read the channel. Forum channels are supported (posts = threads).
One line per message: `- [time] author: text  [附件…] [嵌入…] ↩reply_id ‹msg_id›`.
Attachment URLs are signed CDN links that expire in ~24h — download them now if needed.
"""
import argparse, datetime, json, os, re, subprocess, sys, time, urllib.request, urllib.error

API = "https://discord.com/api/v10"
TZ = datetime.timezone(datetime.timedelta(hours=8))
EPOCH = 1420070400000

p = argparse.ArgumentParser()
p.add_argument("channel")
p.add_argument("out")
p.add_argument("--after", help="only messages on/after this date (UTC+8)")
args = p.parse_args()

r = subprocess.run(["security", "find-generic-password", "-s", "discord-bot-token", "-w"], capture_output=True, text=True)
TOKEN = r.stdout.strip() or os.environ.get("DISCORD_BOT_TOKEN", "")
if not TOKEN:
    sys.exit("no token: security add-generic-password -U -a \"$USER\" -s discord-bot-token -w")


def get(path):
    while True:
        req = urllib.request.Request(API + path, headers={"Authorization": "Bot " + TOKEN, "User-Agent": "discord-dump (local, 1.0)"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(float(json.load(e).get("retry_after", 2)) + 0.2)
                continue
            return {"_error": e.code}


def snowflake(date):
    dt = datetime.datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=TZ)
    return (int(dt.timestamp() * 1000) - EPOCH) << 22


def dump(cid):
    msgs, after = [], snowflake(args.after) if args.after else 0
    while True:
        page = get(f"/channels/{cid}/messages?after={after}&limit=100")
        if not isinstance(page, list):
            print(f"warn: {cid} {page}", file=sys.stderr)
            return msgs
        if not page:
            return msgs
        page.sort(key=lambda m: int(m["id"]))
        msgs += page
        after = page[-1]["id"]
        if len(page) < 100:
            return msgs
        time.sleep(0.3)


ch = get(f"/channels/{args.channel}")
if "_error" in ch:
    sys.exit(f"channel {args.channel}: HTTP {ch['_error']} (bot not in guild / no access?)")
G = ch["guild_id"]

names = {}
members = get(f"/guilds/{G}/members?limit=1000")  # needs Server Members intent; falls back to author names
for m in members if isinstance(members, list) else []:
    names[m["user"]["id"]] = m.get("nick") or m["user"].get("global_name") or m["user"]["username"]

threads = {t["id"]: t for t in get(f"/guilds/{G}/threads/active").get("threads", []) if t.get("parent_id") == args.channel}
for vis in ("public", "private"):  # private needs Manage Threads; 403 is skipped
    before = ""
    while True:
        arch = get(f"/channels/{args.channel}/threads/archived/{vis}?limit=100{before}")
        if not isinstance(arch, dict) or "threads" not in arch:
            break
        for t in arch["threads"]:
            threads[t["id"]] = t
        if not arch.get("has_more") or not arch["threads"]:
            break
        before = "&before=" + arch["threads"][-1]["thread_metadata"]["archive_timestamp"]


def body(cid, msgs):
    out = []
    for m in msgs:
        ts = datetime.datetime.fromtimestamp(((int(m["id"]) >> 22) + EPOCH) / 1000, TZ).strftime("%Y-%m-%d %H:%M")
        text = re.sub(r"<@!?(\d+)>", lambda x: "@" + names.get(x.group(1), x.group(1)), m.get("content", ""))
        who = names.get(m["author"]["id"]) or m["author"].get("global_name") or m["author"]["username"]
        extra = ""
        if m.get("attachments"):
            extra += "  [附件: " + ", ".join(f"{a['filename']} {a['url']}" for a in m["attachments"]) + "]"
        if m.get("embeds"):
            extra += "  [嵌入: " + ", ".join((e.get("title") or e.get("url") or "") for e in m["embeds"]) + "]"
        if (m.get("referenced_message") or {}).get("id"):
            extra += f"  ↩{m['referenced_message']['id']}"
        out.append(f"- [{ts}] {who}: {text.replace(chr(10), ' / ')}{extra} ‹{m['id']}›")
    return f"訊息連結 = https://discord.com/channels/{G}/{cid}/‹訊息ID›\n\n" + "\n".join(out)


parts = [f"# #{ch.get('name', args.channel)}（Discord 訊息，匯出於 {datetime.datetime.now(TZ):%Y-%m-%d %H:%M}）\n"]
total = 0
if ch["type"] != 15:  # forum channels have no messages of their own
    main = dump(args.channel)
    total += len(main)
    parts.append(f"\n## 頻道本體（{len(main)} 則）\n\n{body(args.channel, main)}\n")
for t in sorted(threads.values(), key=lambda t: int(t["id"])):
    tm = dump(t["id"])
    if not tm:
        continue
    total += len(tm)
    parts.append(f"\n## 討論串：{t['name']}（{len(tm)} 則）\n\n{body(t['id'], tm)}\n")
os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
open(args.out, "w").write("\n".join(parts))
print(f"#{ch.get('name')} → {args.out}: {total} msgs, {len(threads)} threads, {len(names)} names resolved")
