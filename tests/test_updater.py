import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch, Mock

import requests

from shortcuty_cli import updater
from shortcuty_cli.http import ShortcutyAPIError
from tests.support import OfflineTest, response


class UpdaterTests(OfflineTest):
    def test_version_source_exists_in_repository_and_is_not_executed(self):
        reply = response(content=b'__version__ = "1.2.3"\nraise RuntimeError("must never execute")')
        with patch("shortcuty_cli.updater.requests.get", return_value=reply) as get:
            result = updater.check_for_updates()
        self.assertEqual(result["version"], "1.2.3")
        self.assertTrue(get.call_args.args[0].endswith("/shortcuty_cli/__init__.py"))
        self.assertEqual(get.call_args.kwargs["timeout"], (5, 5))

    def test_current_version_returns_no_update(self):
        with patch("shortcuty_cli.updater.requests.get", return_value=response(content=b'__version__ = "1.0.0"')):
            self.assertIsNone(updater.check_for_updates())

    def test_invalid_or_missing_metadata_fails_clearly(self):
        for content in (b"<html>404</html>", b"__version__ = 'not-a-version'", b"no_version = 1"):
            with patch("shortcuty_cli.updater.requests.get", return_value=response(content=content)):
                with self.assertRaisesRegex(ShortcutyAPIError, "invalid version metadata"):
                    updater.check_for_updates()

    def test_http_and_network_failures_do_not_return_latest(self):
        with patch("shortcuty_cli.updater.requests.get", return_value=response(404)):
            with self.assertRaisesRegex(ShortcutyAPIError, "HTTP 404"):
                updater.check_for_updates()
        with patch("shortcuty_cli.updater.requests.get", side_effect=requests.Timeout("synthetic")) as get:
            with self.assertRaisesRegex(ShortcutyAPIError, "network"):
                updater.check_for_updates()
            self.assertEqual(get.call_count, 1)

    def test_corrupt_cache_is_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / "last_update_check.json"
            with patch.object(updater, "CACHE_FILE", cache):
                for content in ("[]", "null", "{}", "broken", json.dumps({"last_check": "invalid"}),
                                json.dumps({"last_check": "2026-01-01T00:00:00+00:00"})):
                    cache.write_text(content)
                    self.assertTrue(updater.should_check_updates())

    def test_update_uses_same_python_and_never_shell(self):
        with patch("shortcuty_cli.updater.subprocess.run", return_value=Mock(returncode=0)) as run:
            self.assertTrue(updater.install_update())
        self.assertEqual(run.call_args.args[0][:3], [sys.executable, "-m", "pip"])
        self.assertNotIn("shell", run.call_args.kwargs)
