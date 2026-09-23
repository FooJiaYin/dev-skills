import argparse
import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))
import codex_history as h


THREAD = {"id": "test-session", "name": "Inventory", "cwd": "/project", "createdAt": 100, "updatedAt": 200}


def turn(*items):
    return {"id": "t1", "startedAt": 100, "items": list(items)}


def change(status="completed", path="docs/a.md", move=None):
    return {"id": "f1", "type": "fileChange", "status": status,
            "changes": [{"path": path, "kind": {"type": "update", "move_path": move}}]}


class FakeServer:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.calls = []

    def request(self, method, params):
        self.calls.append((method, params))
        return next(self.replies)


class CodexHistoryTests(unittest.TestCase):
    def test_legacy_export_redacts_stdout_and_file_and_keeps_notes(self):
        secret = "api_key=examplecredential123"
        turns = [turn({"id": "u1", "type": "userMessage", "content": [{"type": "text", "text": secret}]},
                      {"id": "a1", "type": "agentMessage", "text": "noted " + secret})]
        class Server:
            def __enter__(self):
                return self
            def __exit__(self, *_):
                pass
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"CODEX_HOME": tmp, "CODEX_THREAD_ID": THREAD["id"]}), \
                patch.object(h.adapter(), "AppServer", Server), \
                patch.object(h.adapter(), "read_thread", return_value=THREAD), \
                patch.object(h.adapter(), "read_turns", return_value=turns):
            notes_path = h.log_path(THREAD).with_suffix(".notes.jsonl")
            notes_path.parent.mkdir(parents=True)
            notes_path.write_text(json.dumps({"time": "2026-09-23T10:00:00", "body": "decision " + secret}) + "\n")
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                h.legacy_cli("export", [])
            stdout = stream.getvalue()
            self.assertNotIn("examplecredential123", stdout)
            self.assertIn("api_key=[REDACTED]", stdout)
            self.assertIn("decision", stdout)
            output = Path(tmp) / "export.md"
            with contextlib.redirect_stdout(io.StringIO()):
                h.legacy_cli("export", ["-o", str(output)])
            self.assertEqual(output.read_text(), stdout)
            self.assertIn(secret, h.adapter().render_transcript(THREAD, turns, False))

    def test_log_refresh_updates_streaming_items_without_duplicates(self):
        turns = [turn({"id": "a1", "type": "agentMessage", "text": "partial"})]
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"CODEX_HOME": tmp}), \
                patch.object(h.adapter(), "read_thread", return_value=THREAD), \
                patch.object(h.adapter(), "read_turns", return_value=turns):
            path = h.refresh_log(None, THREAD["id"])
            before = path.read_text()
            h.refresh_log(None, THREAD["id"])
            self.assertEqual(before, path.read_text())
            turns[0]["items"][0]["text"] = "finished"
            turns[0]["items"].append(copy.deepcopy(turns[0]["items"][0]))
            h.refresh_log(None, THREAD["id"])
            self.assertNotIn("partial", path.read_text())
            self.assertEqual(path.read_text().count("finished"), 1)

    def test_notes_survive_refresh_and_credentials_are_redacted(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"CODEX_HOME": tmp}), \
                patch.object(h.adapter(), "read_thread", return_value=THREAD), \
                patch.object(h.adapter(), "read_turns", return_value=[]):
            path = h.refresh_log(None, THREAD["id"], note="decision; api_key=examplecredential123")
            h.refresh_log(None, THREAD["id"])
            self.assertIn("decision", path.read_text())
            for p in Path(tmp).rglob("*"):
                if p.is_file():
                    self.assertNotIn("examplecredential123", p.read_text())

    def test_log_write_failure_leaves_previous_view(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "log.md"
            path.write_text("old")
            with patch.object(h.os, "replace", side_effect=OSError("disk failure")):
                with self.assertRaises(OSError):
                    h.atomic_write(path, "new")
            self.assertEqual(path.read_text(), "old")
            self.assertEqual(list(Path(tmp).iterdir()), [path])

    def test_completed_changes_include_both_rename_paths(self):
        self.assertEqual(h.changed_paths(change(move="docs/b.md"), "/project"),
                         ["/project/docs/a.md", "/project/docs/b.md"])
        for status in ("failed", "inProgress", "declined"):
            self.assertEqual(h.changed_paths(change(status), "/project"), [])

    def test_failed_changes_are_not_rendered_as_writes(self):
        recs = list(h.records(THREAD, [turn(change("failed"))]))
        self.assertFalse(any(tag == "write" for _, tag, _ in recs))

    def test_mentions_and_shell_commands_do_not_establish_file_authorship(self):
        items = [{"id": "a", "type": "agentMessage", "text": "docs/a.md"},
                 {"id": "b", "type": "commandExecution", "command": "touch docs/a.md", "status": "completed"}]
        self.assertIsNone(h.match_thread(THREAD, [turn(*items)], [], "docs/a.md"))

    def test_path_matching_respects_components_and_space(self):
        turns = [turn(change(path="my docs/a.md"))]
        self.assertIsNotNone(h.match_thread(THREAD, turns, [], "my docs/a.md"))
        self.assertIsNone(h.match_thread(THREAD, turns, [], "docs/a.md"))
        self.assertIsNone(h.match_thread(THREAD, turns, [], "/other/my docs/a.md"))

    def test_topic_and_file_filters_are_combined(self):
        turns = [turn(change(), {"id": "a", "type": "agentMessage", "text": "delivery assessment"})]
        self.assertIsNotNone(h.match_thread(THREAD, turns, ["delivery", "assessment"], "docs/a.md"))
        self.assertIsNone(h.match_thread(THREAD, turns, ["missing"], "docs/a.md"))
        self.assertIsNone(h.match_thread(THREAD, turns, ["delivery"], "other.md"))

    def test_system_skill_wrappers_do_not_match_topics(self):
        item = {"type": "userMessage", "content": [{"type": "text", "text": "<skill>irrelevantkeyword</skill> real request"}]}
        self.assertNotIn("irrelevantkeyword", h.search_text(item))
        self.assertIn("real request", h.search_text(item))

    def test_until_includes_entire_day(self):
        from datetime import datetime
        epoch = datetime(2026, 9, 23, 23, 59).timestamp()
        thread = dict(THREAD, createdAt=epoch, updatedAt=epoch)
        self.assertIsNotNone(h.match_thread(thread, [], [], None, until="2026-09-23"))
        self.assertIsNone(h.match_thread(thread, [], [], None, until="2026-09-22"))

    def test_thread_listing_paginates_active_and_archived_and_deduplicates(self):
        server = FakeServer([{"data": [THREAD], "nextCursor": "next"},
                             {"data": [THREAD], "nextCursor": None},
                             {"data": [dict(THREAD, id="archived")], "nextCursor": None}])
        result = list(h.list_threads(server, "/project"))
        self.assertEqual([t["id"] for t in result], ["test-session", "archived"])
        self.assertEqual(server.calls[1][1]["cursor"], "next")
        self.assertTrue(server.calls[2][1]["archived"])
        self.assertTrue(all(c[1]["cwd"] == "/project" for c in server.calls))

    def test_repeated_cursor_is_an_error(self):
        server = FakeServer([{"data": [], "nextCursor": "x"}, {"data": [], "nextCursor": "x"}])
        with self.assertRaises(SystemExit):
            list(h.list_threads(server))

    def test_id_prefix_does_not_guess_among_matches(self):
        with patch.object(h, "list_threads", return_value=[{"id": "abc1"}, {"id": "abc2"}]):
            with self.assertRaises(SystemExit):
                h.resolve_id(None, "abc")

    def test_current_session_requires_host_identity(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit):
                h.resolve_id(None, "current")

    def test_search_entry_routes_to_codex_without_reading_claude(self):
        p = Path(__file__).resolve().parents[1] / "skills/find-session/scripts/search.py"
        spec = importlib.util.spec_from_file_location("session_search", p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        with patch.object(sys, "argv", [str(p), "--open-id", "current"]), \
                patch.dict(os.environ, {"CODEX_THREAD_ID": "our-session"}), \
                patch.object(h, "search_main", return_value=0) as search, \
                patch.object(mod, "find_log_by_id", side_effect=AssertionError("Claude accessed")):
            self.assertEqual(mod.main(), 0)
            self.assertEqual(search.call_args[0][0].open_id, "current")

    def test_explicit_claude_override_preserves_claude_lookup(self):
        p = Path(__file__).resolve().parents[1] / "skills/find-session/scripts/search.py"
        spec = importlib.util.spec_from_file_location("session_search", p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        with patch.object(sys, "argv", [str(p), "--host", "claude", "--open-id", "known"]), \
                patch.dict(os.environ, {"CODEX_THREAD_ID": "our-session"}), \
                patch.object(h, "search_main", side_effect=AssertionError("Codex accessed")), \
                patch.object(mod, "find_log_by_id", return_value=Path("known.log.md")), \
                patch.object(mod, "open_in_editor", return_value=0):
            self.assertEqual(mod.main(), 0)


if __name__ == "__main__":
    unittest.main()
