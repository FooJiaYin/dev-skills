"""Merge Claude and Codex history without conflating their evidence or IDs."""
from contextlib import ExitStack
from datetime import date, datetime
import os
from pathlib import Path
import sys

import codex_history as codex


def timestamp_key(hit):
    value = hit['time']
    if isinstance(value, (int, float)):
        return value
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
    except (ValueError, AttributeError, TypeError):
        return 0


def open_hit(hit, claude, server):
    if hit['host'] == 'codex':
        path = codex.refresh_log(server, hit['id'])
        codex.open_in_editor(path)
        return 0
    path = claude.log_path_for(hit['data'])
    if path:
        return claude.open_in_editor(path)
    print(f"# {hit['id']} has no Claude log; source: {hit['data']['path']}")
    return 1


def search_main(args, claude):
    for value in (args.since, args.until):
        if value:
            date.fromisoformat(value)
    if args.limit < 0 or (args.open is not None and args.open < 1):
        raise SystemExit('--limit must be nonnegative; --open must be at least 1')
    failures = set()

    def failed(key, exc):
        if key not in failures:
            print(f'# incomplete: {key}: {exc}', file=sys.stderr)
        failures.add(key)

    with ExitStack() as stack:
        try:
            server = stack.enter_context(codex.adapter().AppServer())
        except (Exception, SystemExit) as exc:
            failed('Codex backend', exc)
            server = None
        if args.open_id:
            matches = []
            try:
                sources = dict(claude.iter_session_files('all-bak', args.cwd))
                # Logs remain useful after the native transcript is removed.
                for path in claude.PROJECTS_ROOT.glob('*/*.log.md'):
                    sources.setdefault(path.name[:-len('.log.md')], path)
                for sid, path in sources.items():
                    if sid.startswith(args.open_id):
                        matches.append({'host': 'claude', 'id': sid, 'data': {'path': str(path)}})
            except OSError as exc:
                failed('Claude listing', exc)
            if server is not None:
                try:
                    for thread in codex.list_threads(server):
                        if thread['id'].startswith(args.open_id):
                            matches.append({'host': 'codex', 'id': thread['id']})
                except (Exception, SystemExit) as exc:
                    failed('Codex listing', exc)
            if failures:
                print('# Cannot resolve an ID uniquely while a backend is unreadable; specify --host.')
                return 2
            if len(matches) != 1:
                print(f'# ID {args.open_id!r}: {len(matches)} matches; specify --host and a unique/full ID.')
                return 1
            return open_hit(matches[0], claude, server)

        scopes = ['cwd', 'all', 'all-bak']
        scopes = scopes[scopes.index(args.scope):] if args.escalate else [args.scope]
        me_claude = os.environ.get('CLAUDE_CODE_SESSION_ID') or os.environ.get('CLAUDE_SESSION_ID')
        me_codex = os.environ.get('CODEX_THREAD_ID') or os.environ.get('CODEX_SESSION_ID')
        turn_cache, candidate_cache, claude_cache = {}, {}, {}
        hits = []
        for scope in scopes:
            try:
                files = list(claude.iter_session_files(scope, args.cwd))
            except OSError as exc:
                failed('Claude listing', exc)
                files = []
            threads = []
            if server is not None:
                key = 'cwd' if scope == 'cwd' else 'all'
                try:
                    if key not in candidate_cache:
                        candidate_cache[key] = list(codex.list_threads(server, (args.cwd or os.getcwd()) if key == 'cwd' else None))
                    threads = candidate_cache[key]
                except (Exception, SystemExit) as exc:
                    failed('Codex listing', exc)
            queries = [[args.topic]]
            if len((args.topic or '').split()) > 1:
                queries.append(args.topic.split())
            for topics in queries:
                hits = []
                for sid, path in files:
                    if sid == me_claude:
                        continue
                    try:
                        records = []
                        for topic in topics:
                            key = (str(path), topic)
                            if key not in claude_cache:
                                until = args.until + 'T23:59:59.999999' if args.until else None
                                claude_cache[key] = claude.scan_session(path, topic, args.touched, args.since, until)
                            records.append(claude_cache[key])
                        if all(records):
                            rec = dict(records[0])
                            rec['topic_hits'] = [x for r in records for x in r['topic_hits']]
                            hits.append({'host': 'claude', 'id': sid, 'time': rec['first_ts'], 'data': rec})
                    except Exception as exc:
                        failed(f'Claude {sid}', exc)
                for thread in threads:
                    sid = thread['id']
                    if sid == me_codex or f'Codex {sid}' in failures:
                        continue
                    try:
                        if sid not in turn_cache:
                            turn_cache[sid] = codex.adapter().read_turns(server, sid)
                        rec = codex.match_thread(thread, turn_cache[sid], topics, args.touched, args.since, args.until)
                        if rec:
                            hits.append({'host': 'codex', 'id': sid, 'time': thread.get('createdAt', 0), 'data': rec})
                    except (Exception, SystemExit) as exc:
                        failed(f'Codex {sid}', exc)
                if hits:
                    if topics != [args.topic]:
                        print('# no literal match in scope; matched all words')
                    break
            if hits:
                break
        hits.sort(key=timestamp_key, reverse=True)
        total = len(hits)
        if args.limit:
            hits = hits[:args.limit]
        print(f'# host=all scope={scope} matches={total} shown={len(hits)} unreadable={len(failures)}')
        for i, hit in enumerate(hits, 1):
            rec = hit['data']
            title = (rec.get('title') or rec.get('first_user') or '(untitled)') if hit['host'] == 'claude' else (rec['thread'].get('name') or rec['thread'].get('preview') or '(untitled)')
            stamp = codex.adapter().timestamp(timestamp_key(hit))
            print(codex.redact(f"{i}. {stamp}  [{hit['host']}] {hit['id']}  {' '.join(title.split())[:120]}"))
            if hit['host'] == 'claude' and args.output == 'full':
                print(codex.redact(claude.format_full([rec])))
            elif hit['host'] == 'codex' and args.output == 'graph':
                print(f"  forkedFromId={rec['thread'].get('forkedFromId') or '(not reported)'}")
            elif hit['host'] == 'codex' and args.output == 'full':
                print(f"  cwd: {rec['thread'].get('cwd', '')}\n  log: {codex.log_path(rec['thread'])}")
                for text in rec['snippets']:
                    print('  match: ' + codex.redact(codex.adapter().truncate(text, 400, 5)))
                for path in rec['paths']:
                    print('  fileChange: ' + path)
        if args.output == 'graph':
            claude_hits = [h['data'] for h in hits if h['host'] == 'claude']
            if claude_hits:
                print('# Claude fork graph (within returned Claude results)')
                print(codex.redact(claude.format_graph(claude_hits)))
        if args.touched:
            print('# Codex write evidence: completed fileChange only; shell/MCP writes may be absent.')
        if hits:
            print('# Resume: claude --resume <Claude ID> | codex resume <Codex ID>')
        opened = 0
        if args.open is not None:
            if args.open > len(hits):
                print(f'# --open {args.open}: only {len(hits)} hits')
                opened = 1
            else:
                opened = open_hit(hits[args.open - 1], claude, server)
        return 2 if failures else (opened if hits else 1)
