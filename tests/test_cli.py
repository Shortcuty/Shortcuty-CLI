import inspect
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from click.testing import CliRunner

from shortcuty_cli.cli import cli
from shortcuty_cli.config import get_api_key
from shortcuty_cli.http import ShortcutyAPIError
from tests.support import OfflineTest, UUID, URL, KEY


class CLITests(OfflineTest):
    def setUp(self):
        super().setUp()
        options = {"mix_stderr": False} if "mix_stderr" in inspect.signature(CliRunner).parameters else {}
        self.runner = CliRunner(**options)
        cache = patch("shortcuty_cli.cli.update_cache_timestamp")
        cache.start()
        self.addCleanup(cache.stop)

    def invoke(self, *args):
        return self.runner.invoke(cli, ["--no-check-updates", *args], env={"SHORTCUTY_API_KEY": KEY})

    def test_help_and_version_do_not_check_updates_or_require_auth(self):
        with patch("shortcuty_cli.cli.check_for_updates") as check:
            for args in (["--help"], ["--version"], ["sign", "--help"], ["update", "--help"]):
                result = self.runner.invoke(cli, args)
                self.assertEqual(result.exit_code, 0, result.output)
            check.assert_not_called()

    def test_private_command_requires_key(self):
        result = self.runner.invoke(cli, ["--no-check-updates", "list"])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("API key required", result.stderr)

    def test_config_precedence_does_not_read_or_write_credentials(self):
        with patch.dict("os.environ", {"SHORTCUTY_API_KEY": KEY}):
            self.assertEqual(get_api_key(), KEY)
            self.assertEqual(get_api_key("cli-synthetic"), "cli-synthetic")

    def test_update_false_and_empty_description_are_sent(self):
        with patch("shortcuty_cli.cli.ShortcutyAPIClient.update_shortcut", return_value={"message": "Updated"}) as update:
            result = self.invoke("update", UUID, "--no-requires-ios26-ai", "--description", "")
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIs(update.call_args.kwargs["requires_ios26_ai"], False)
            self.assertEqual(update.call_args.kwargs["description"], "")

    def test_clear_fields_visibility_and_help(self):
        with patch("shortcuty_cli.cli.ShortcutyAPIClient.update_shortcut", return_value={}) as update:
            result = self.invoke("update", UUID, "--clear-description", "--clear-category", "--visibility", "private")
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertTrue(update.call_args.kwargs["clear_description"])
            self.assertTrue(update.call_args.kwargs["clear_category"])
            self.assertEqual(update.call_args.kwargs["visibility"], "private")
        result = self.invoke("update", UUID, "--clear-description", "--description", "ambiguous")
        self.assertEqual(result.exit_code, 2)

    def test_pagination_and_timeout_validation(self):
        for args in (("list", "--page", "0"), ("list", "--per-page", "-1"), ("--timeout", "0", "categories")):
            result = self.invoke(*args)
            self.assertEqual(result.exit_code, 2, result.output)

    def test_create_json_shape_remains_shortcut_object(self):
        body = {"shortcut": {"uuid": UUID, "description": None}, "scan_queued": False}
        with patch("shortcuty_cli.cli.ShortcutyAPIClient.create_shortcut", return_value=body):
            result = self.invoke("--json", "create", "--sharing-url", URL)
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(json.loads(result.stdout), body["shortcut"])

    def test_json_commands_skip_automatic_update_network_check(self):
        with patch("shortcuty_cli.cli.ShortcutyAPIClient.list_shortcuts", return_value={"shortcuts": [], "pages": 0}), \
                patch("shortcuty_cli.cli.check_for_updates") as check:
            result = self.runner.invoke(cli, ["--json", "list"], env={"SHORTCUTY_API_KEY": KEY})
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(json.loads(result.stdout)["shortcuts"], [])
        check.assert_not_called()

    def test_sign_needs_no_key_json_stdout_and_progress_stderr(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "fixture.shortcut"
            source.write_bytes(b"synthetic fixture")
            with patch("shortcuty_cli.cli.sign_shortcut", return_value={"output": "signed.shortcut"}) as sign, \
                    patch("shortcuty_cli.cli.check_for_updates") as check:
                result = self.runner.invoke(cli, ["--json", "sign", str(source), "--timeout", "900", "-o", "out.shortcut"])
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertEqual(json.loads(result.stdout), {"output": "signed.shortcut"})
            self.assertIn("Signing shortcut", result.stderr)
            self.assertEqual(sign.call_args.kwargs["timeout"], 900)
            self.assertEqual(sign.call_args.kwargs["output"], "out.shortcut")
            check.assert_not_called()

    def test_explicit_update_failure_not_reported_as_latest(self):
        with patch("shortcuty_cli.cli.check_for_updates", side_effect=ShortcutyAPIError("Update check failed: HTTP 404")):
            result = self.invoke("check-updates")
        self.assertEqual(result.exit_code, 1)
        self.assertNotIn("latest version", result.output)

    def test_check_updates_json_is_machine_readable(self):
        with patch("shortcuty_cli.cli.check_for_updates", return_value=None):
            result = self.invoke("--json", "check-updates")
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertFalse(json.loads(result.stdout)["update_available"])
