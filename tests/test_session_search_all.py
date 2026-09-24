import contextlib
import importlib.util
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'bin'))
import codex_history as h
import session_search_all as combined

spec = importlib.util.spec_from_file_location('search_both_tests', ROOT / 'skills/find-session/scripts/search.py')
search = importlib.util.module_from_spec(spec)
spec.loader.exec_module(search)


class CombinedSearchTests(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        tmp = self.stack.enter_context(tempfile.TemporaryDirectory())
        self.projects = Path(tmp)
        self.stack.enter_context(patch.object(search, 'PROJECTS_ROOT', self.projects))
        self.stack.enter_context(patch.dict(os.environ, {'CODEX_THREAD_ID': 'current-codex', 'CLAUDE_CODE_SESSION_ID': 'current-claude'}))
        self.adapter = h.adapter()
        self.factory = self.stack.enter_context(patch.object(self.adapter, 'AppServer'))
        self.listing = self.stack.enter_context(patch.object(h, 'list_threads', return_value=[]))
        self.turns = self.stack.enter_context(patch.object(self.adapter, 'read_turns', return_value=[{
            'id': 'turn', 'items': [{'type': 'userMessage', 'content': [{'type': 'text', 'text': 'needle'}]}]}]))

    def claude(self, sid='claude-hit', project='-project', text='needle', day='01-01'):
        folder = self.projects / project
        folder.mkdir(exist_ok=True)
        (folder / f'{sid}.jsonl').write_text('')
        (folder / f'{sid}.log.md').write_text(f'# Title · session {sid} · /project · main\n[{day} 00:00 user] {text}\n')

    def codex(self, sid='codex-hit'):
        # Later than fixture Claude logs, independently of the calendar year.
        return {'id': sid, 'createdAt': 4102444800, 'cwd': '/project', 'name': 'Codex result'}

    def run_search(self, *flags):
        out, err = io.StringIO(), io.StringIO()
        with patch.object(sys, 'argv', ['search.py', '--cwd', '/project', *flags]), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = search.main()
        return code, out.getvalue(), err.getvalue()

    def test_default_merges_sources_and_global_limit_open(self):
        self.claude()
        self.listing.return_value = [self.codex()]
        with patch.object(combined, 'open_hit', return_value=0) as opener:
            code, out, _ = self.run_search('--topic', 'needle', '--limit', '2', '--open', '2')
        self.assertEqual(code, 0)
        self.assertLess(out.index('[codex]'), out.index('[claude]'))
        self.assertEqual(opener.call_args.args[0]['host'], 'claude')
        code, out, _ = self.run_search('--topic', 'needle', '--limit', '1')
        self.assertIn('matches=2 shown=1', out)
        self.assertNotIn('[claude]', out)

    def test_escalation_waits_for_both_sources_and_stops_at_cwd(self):
        self.claude(project='-elsewhere')
        self.listing.return_value = [self.codex()]
        code, out, _ = self.run_search('--topic', 'needle', '--escalate')
        self.assertEqual(code, 0)
        self.assertIn('scope=cwd', out)
        self.assertNotIn('[claude]', out)
        self.listing.assert_called_once()

    def test_codex_failure_preserves_claude_results_and_reports_incomplete(self):
        self.claude()
        self.factory.side_effect = SystemExit('unavailable')
        code, out, err = self.run_search('--topic', 'needle')
        self.assertEqual(code, 2)
        self.assertIn('[claude]', out)
        self.assertIn('incomplete', err)

    def test_explicit_claude_does_not_start_codex(self):
        self.claude()
        code, _, _ = self.run_search('--host', 'claude', '--topic', 'needle')
        self.assertEqual(code, 0)
        self.factory.assert_not_called()

    def test_ambiguous_cross_host_id_does_not_open(self):
        self.claude(sid='shared-claude')
        self.listing.return_value = [self.codex('shared-codex')]
        with patch.object(combined, 'open_hit') as opener:
            code, out, _ = self.run_search('--open-id', 'shared')
        self.assertEqual(code, 1)
        self.assertIn('2 matches', out)
        opener.assert_not_called()

    def test_excludes_current_sessions_on_both_hosts(self):
        self.claude(sid='current-claude')
        self.listing.return_value = [self.codex('current-codex')]
        code, out, _ = self.run_search('--topic', 'needle')
        self.assertEqual(code, 1)
        self.assertIn('matches=0', out)

    def test_missing_claude_directory_still_searches_codex(self):
        self.listing.return_value = [self.codex()]
        with patch.object(search, 'PROJECTS_ROOT', self.projects / 'missing'):
            code, out, _ = self.run_search('--topic', 'needle', '--scope', 'all')
        self.assertEqual(code, 0)
        self.assertIn('[codex]', out)

    def test_open_id_finds_log_without_original_transcript(self):
        self.claude()
        (self.projects / '-project/claude-hit.jsonl').unlink()
        with patch.object(search, 'open_in_editor', return_value=0) as opened:
            code, _, _ = self.run_search('--open-id', 'claude-hit')
        self.assertEqual(code, 0)
        self.assertEqual(opened.call_args.args[0].suffix, '.md')

    def test_all_word_fallback_happens_before_expanding_scope(self):
        self.claude(text='needle separated other')
        self.claude(sid='elsewhere', project='-elsewhere', text='needle other')
        code, out, _ = self.run_search('--topic', 'needle other', '--escalate')
        self.assertEqual(code, 0)
        self.assertIn('scope=cwd', out)
        self.assertIn('claude-hit', out)
        self.assertNotIn('elsewhere', out)


if __name__ == '__main__':
    unittest.main()
