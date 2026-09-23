import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "bin/codex-log-hook.py"
sys.path.insert(0, str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location("codex_log_hook", SCRIPT)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)


class Server:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass


class HookTests(unittest.TestCase):
    def test_stop_refreshes_explicit_session_and_returns_valid_json(self):
        payload = {"hook_event_name": "Stop", "session_id": "known-id"}
        with patch.object(hook, "refresh_log", return_value=Path("/tmp/log.md")) as refresh:
            self.assertEqual(hook.handle(payload, server_factory=Server), {})
        refresh.assert_called_once()
        self.assertEqual(refresh.call_args.args[1], "known-id")

    def test_resume_injects_short_log_pointer(self):
        payload = {"hook_event_name": "SessionStart", "session_id": "known-id", "source": "resume"}
        with patch.object(hook, "refresh_log", return_value=Path("/tmp/log.md")):
            result = hook.handle(payload, server_factory=Server)
        self.assertEqual(result["hookSpecificOutput"]["hookEventName"], "SessionStart")
        self.assertIn("/tmp/log.md", result["hookSpecificOutput"]["additionalContext"])

    def test_missing_id_and_failed_startup_are_nonblocking(self):
        with patch.object(hook, "refresh_log", side_effect=SystemExit("not ready")):
            self.assertEqual(hook.handle({"hook_event_name": "SessionStart", "session_id": "known-id"}, server_factory=Server), {})
        self.assertEqual(hook.handle({"hook_event_name": "Stop"}, server_factory=Server), {})

    def test_post_tool_refresh_is_throttled_but_stop_is_not(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"CODEX_HOME": tmp}):
            payload = {"session_id": "known-id", "cwd": "/project", "hook_event_name": "PostToolUse"}
            path = hook.log_path({"id": "known-id", "cwd": "/project"})
            path.parent.mkdir(parents=True)
            path.write_text("fresh")
            with patch.object(hook, "refresh_log") as refresh:
                self.assertEqual(hook.handle(payload, server_factory=Server), {})
                refresh.assert_not_called()
                payload["hook_event_name"] = "Stop"
                self.assertEqual(hook.handle(payload, server_factory=Server), {})
                refresh.assert_called_once()

    def test_parallel_post_tool_hook_skips_when_refresh_is_in_progress(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"CODEX_HOME": tmp}):
            payload = {"session_id": "known-id", "cwd": "/project", "hook_event_name": "PostToolUse"}
            path = hook.log_path({"id": "known-id", "cwd": "/project"})

            def refresh(*_args):
                # Reenter while the first hook holds its gate, as a second
                # process would when two background hooks finish together.
                self.assertEqual(hook.handle(payload, server_factory=Server), {})
                return path

            with patch.object(hook, "refresh_log", side_effect=refresh) as called:
                self.assertEqual(hook.handle(payload, server_factory=Server), {})
                called.assert_called_once()

    def test_cli_emits_json_for_stop(self):
        payload = json.dumps({"hook_event_name": "Stop", "session_id": "known-id"})
        with patch.object(hook.sys, "stdin", io.StringIO(payload)), \
                patch.object(hook, "refresh_log", return_value=Path("/tmp/log.md")), \
                patch.object(hook, "adapter") as adapter, \
                patch.object(hook.sys, "stdout", new_callable=io.StringIO) as output:
            adapter.return_value.AppServer.return_value.__enter__.return_value = Server()
            hook.main()
            self.assertEqual(json.loads(output.getvalue()), {})


if __name__ == "__main__":
    unittest.main()
