import hashlib
import os
from pathlib import Path
import plistlib
import tempfile
from unittest.mock import patch

import requests

from shortcuty_cli.http import ShortcutyAPIError
from shortcuty_cli.signing import sign_shortcut, download_filename, safe_filename, SIGN_URL
from tests.support import OfflineTest, response, session_for


class SigningTests(OfflineTest):
    def setUp(self):
        super().setUp()
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / "My Shortcut.shortcut"
        self.unsigned = plistlib.dumps({"WFWorkflowActions": [], "WFWorkflowName": "Synthetic"})
        self.source.write_bytes(self.unsigned)
        self.signed = b"AEA1synthetic signed fixture, not a real signature"
        self.output = self.root / "result.shortcut"

    def signed_response(self, **overrides):
        headers = {
            "Content-Type": "application/octet-stream", "Content-Length": str(len(self.signed)),
            "Content-Disposition": "attachment; filename=\"fallback.shortcut\"; filename*=UTF-8''Caf%C3%A9%20%E2%80%94%20Signed.shortcut",
            "X-Shortcut-Input-SHA256": hashlib.sha256(self.unsigned).hexdigest(),
            "X-Shortcut-Signed-SHA256": hashlib.sha256(self.signed).hexdigest(),
        }
        headers.update(overrides)
        return response(content=self.signed, headers=headers)

    def run_sign(self, reply=None, **options):
        session, adapter = session_for(reply if reply is not None else self.signed_response())
        with patch("shortcuty_cli.signing.requests.Session", return_value=session):
            result = sign_shortcut(str(self.source), **options)
        return result, adapter

    def test_streaming_multipart_contract_and_atomic_save(self):
        result, adapter = self.run_sign(output=self.output)
        self.assertEqual(self.output.read_bytes(), self.signed)
        self.assertEqual(self.source.read_bytes(), self.unsigned)
        self.assertEqual(result["size"], len(self.signed))
        prepared, options, upload = adapter.calls[0]
        self.assertEqual(prepared.url, SIGN_URL)
        self.assertEqual(prepared.method, "POST")
        self.assertNotIn("Authorization", prepared.headers)
        self.assertIn(b'name="file"; filename="My Shortcut.shortcut"', upload)
        self.assertIn(self.unsigned, upload)
        self.assertTrue(hasattr(prepared.body, "read"))
        self.assertEqual(int(prepared.headers["Content-Length"]), len(upload))
        self.assertEqual(options["timeout"], (10, 300))
        self.assertTrue(options["stream"])
        self.assertEqual(list(self.root.glob(".shortcuty-*")), [])

    def test_unicode_server_filename_used_in_current_directory(self):
        previous = os.getcwd()
        try:
            os.chdir(self.root)
            result, _ = self.run_sign()
        finally:
            os.chdir(previous)
        self.assertEqual(result["output"], "Café — Signed.shortcut")
        self.assertEqual((self.root / result["output"]).read_bytes(), self.signed)

    def test_explicit_output_and_custom_timeout(self):
        result, adapter = self.run_sign(output=self.output, timeout=900)
        self.assertEqual(result["output"], str(self.output))
        self.assertEqual(adapter.calls[0][1]["timeout"], (10, 900))

    def test_compressed_transfer_length_is_not_decoded_file_length(self):
        # requests iter_content yields decoded bytes; Content-Length counts wire bytes.
        self.run_sign(self.signed_response(**{"Content-Encoding": "gzip", "Content-Length": "999"}),
                      output=self.output)
        self.assertEqual(self.output.read_bytes(), self.signed)

    def test_signer_does_not_use_implicit_netrc_credentials(self):
        session, adapter = session_for(self.signed_response())
        session.trust_env = True
        with patch("shortcuty_cli.signing.requests.Session", return_value=session), \
                patch("requests.sessions.get_netrc_auth") as netrc:
            sign_shortcut(self.source, output=self.output)
        netrc.assert_not_called()
        self.assertNotIn("Authorization", adapter.calls[0][0].headers)

    def test_existing_output_and_input_refused_before_upload(self):
        self.output.write_bytes(b"keep")
        for destination in (self.output, self.source):
            with patch("shortcuty_cli.signing.requests.Session") as factory:
                with self.assertRaisesRegex(ShortcutyAPIError, "already exists"):
                    sign_shortcut(self.source, output=destination)
                factory.assert_not_called()
        self.assertEqual(self.output.read_bytes(), b"keep")
        self.assertEqual(self.source.read_bytes(), self.unsigned)

    def test_force_can_atomically_replace_existing_output_or_input(self):
        self.output.write_bytes(b"old")
        self.run_sign(output=self.output, force=True)
        self.assertEqual(self.output.read_bytes(), self.signed)
        self.run_sign(output=self.source, force=True)
        self.assertEqual(self.source.read_bytes(), self.signed)

    def test_no_clobber_if_destination_appears_during_download(self):
        reply = self.signed_response()
        def chunks(_size):
            self.output.write_bytes(b"created concurrently")
            yield self.signed
        reply.iter_content = chunks
        with self.assertRaisesRegex(ShortcutyAPIError, "already exists"):
            self.run_sign(reply, output=self.output)
        self.assertEqual(self.output.read_bytes(), b"created concurrently")
        self.assertEqual(list(self.root.glob(".shortcuty-*")), [])

    def test_symlink_not_followed_without_force(self):
        try:
            self.output.symlink_to(self.source)
        except OSError:
            self.skipTest("Symlinks are unavailable on this filesystem")
        with self.assertRaises(ShortcutyAPIError):
            self.run_sign(output=self.output)
        self.assertEqual(self.source.read_bytes(), self.unsigned)

    def test_symlink_force_replaces_link_and_preserves_its_target(self):
        try:
            self.output.symlink_to(self.source)
        except OSError:
            self.skipTest("Symlinks are unavailable on this filesystem")
        self.run_sign(output=self.output, force=True)
        self.assertFalse(self.output.is_symlink())
        self.assertEqual(self.source.read_bytes(), self.unsigned)

    def test_invalid_format_hash_or_length_leaves_existing_file_intact(self):
        for header in ({"X-Shortcut-Input-SHA256": "0" * 64},
                       {"X-Shortcut-Signed-SHA256": "0" * 64},
                       {"Content-Length": "1000"}):
            with self.subTest(header=header):
                self.output.write_bytes(b"keep")
                with self.assertRaisesRegex(ShortcutyAPIError, "mismatch"):
                    self.run_sign(self.signed_response(**header), output=self.output, force=True)
                self.assertEqual(self.output.read_bytes(), b"keep")
        reply = self.signed_response()
        reply._content = b"not a signed file"
        with self.assertRaisesRegex(ShortcutyAPIError, "AEA1"):
            self.run_sign(reply, output=self.output, force=True)
        self.assertEqual(self.output.read_bytes(), b"keep")
        self.assertEqual(list(self.root.glob(".shortcuty-*")), [])

    def test_interrupted_download_cleans_temp_and_keeps_output(self):
        reply = self.signed_response()
        def chunks(_size):
            yield b"AEA1partial"
            raise requests.ConnectionError("connection lost")
        reply.iter_content = chunks
        self.output.write_bytes(b"keep")
        with self.assertRaisesRegex(ShortcutyAPIError, "no output saved"):
            self.run_sign(reply, output=self.output, force=True)
        self.assertEqual(self.output.read_bytes(), b"keep")
        self.assertEqual(list(self.root.glob(".shortcuty-*")), [])

    def test_structured_errors_not_retried(self):
        for status, code in ((422, "already_signed"), (503, "signing_queue_full"), (504, "signer_timeout")):
            with self.subTest(status=status):
                reply = response(status, {"success": False, "error": {"code": code, "message": "Synthetic error"}},
                                 headers={"Content-Type": "application/json", "Retry-After": "1"})
                session, adapter = session_for(reply)
                with patch("shortcuty_cli.signing.requests.Session", return_value=session):
                    with self.assertRaisesRegex(ShortcutyAPIError, code) as raised:
                        sign_shortcut(self.source, output=self.output)
                self.assertEqual(raised.exception.status_code, status)
                if status == 503:
                    self.assertIn("Retry-After: 1", str(raised.exception))
                self.assertEqual(len(adapter.calls), 1)
                self.assertFalse(self.output.exists())

    def test_proxy_413_is_useful_and_does_not_save_html(self):
        with self.assertRaisesRegex(ShortcutyAPIError, "size limit"):
            self.run_sign(response(413, content=b"<html>Too large</html>"), output=self.output)
        self.assertFalse(self.output.exists())

    def test_unexpected_json_or_async_response_rejected(self):
        for reply in (response(200, {"success": True}), response(202, {"job_id": "not-supported"})):
            with self.assertRaisesRegex(ShortcutyAPIError, "HTTP 200 signed binary"):
                self.run_sign(reply, output=self.output)
            self.assertFalse(self.output.exists())

    def test_empty_or_wrong_extension_file_not_uploaded(self):
        self.source.write_bytes(b"")
        with self.assertRaisesRegex(ShortcutyAPIError, "empty"):
            self.run_sign(output=self.output)
        with self.assertRaisesRegex(ShortcutyAPIError, "unsigned .shortcut"):
            sign_shortcut(self.root / "wrong.txt", output=self.output)

    def test_missing_directory_does_not_upload(self):
        with patch("shortcuty_cli.signing.requests.Session") as factory:
            with self.assertRaisesRegex(ShortcutyAPIError, "directory"):
                sign_shortcut(self.source, output=self.root / "missing" / "result.shortcut")
            factory.assert_not_called()

    def test_filename_sanitization_handles_paths_and_reserved_names(self):
        for value in ("../../outside.shortcut", "C:\\folder\\outside.shortcut", "/tmp/outside.shortcut"):
            self.assertEqual(safe_filename(value), "outside.shortcut")
        self.assertEqual(safe_filename("NUL.shortcut"), "workflow — Signed.shortcut")
        self.assertEqual(safe_filename("\x00evil?.shortcut"), "_evil_.shortcut")
        self.assertLessEqual(len(safe_filename("é" * 500).encode()), 240)
        self.assertEqual(download_filename(None, "Example — Unsigned.shortcut"), "Example — Signed.shortcut")
        self.assertEqual(download_filename(None, "Designed.shortcut"), "Designed — Signed.shortcut")
        self.assertEqual(download_filename("attachment; filename*=UTF-8''..%2F..%2Fevil.shortcut", "input"), "evil.shortcut")
