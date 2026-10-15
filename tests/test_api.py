import json
from pathlib import Path
import tempfile
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import requests

from shortcuty_cli.api_client import ShortcutyAPIClient, ShortcutyAPIError, validate_icloud_url, validate_image_file
from shortcuty_cli.formatters import format_shortcut, format_history, format_message, format_screenshot, format_shortcut_list
from tests.support import OfflineTest, response, MemoryAdapter, UUID, URL, KEY


class APITests(OfflineTest):
    def client(self, *responses, **kwargs):
        client = ShortcutyAPIClient(KEY, **kwargs)
        adapter = MemoryAdapter(*responses)
        client.session.trust_env = False
        client.session.mount("https://", adapter)
        self.addCleanup(client.close)
        return client, adapter

    def test_explicit_bearer_not_replaced_by_netrc_credentials(self):
        client, adapter = self.client(response(body={"categories": []}))
        client.session.trust_env = True
        with patch("requests.sessions.get_netrc_auth") as netrc:
            client.get_categories()
        netrc.assert_not_called()
        self.assertEqual(adapter.calls[0][0].headers["Authorization"], "Bearer " + KEY)

    def test_create_json_uses_flat_current_fields_and_native_booleans(self):
        client, adapter = self.client(response(201, {"shortcut": {"uuid": UUID}}))
        result = client.create_shortcut(URL, requires_ios26_ai=False, auto_submit=True, visibility="private")
        self.assertEqual(result["shortcut"]["uuid"], UUID)
        prepared, options, body = adapter.calls[0]
        self.assertEqual(json.loads(body), {"sharing_url": URL, "requires_ios26_ai": False,
                                          "auto_submit": True, "visibility": "private"})
        self.assertEqual(prepared.headers["Content-Type"], "application/json")
        self.assertEqual(options["timeout"], (10, 60))
        self.assertEqual(prepared.headers["Authorization"], "Bearer " + KEY)

    def test_form_serializes_false_as_false_and_encodes_text(self):
        client, adapter = self.client(response(201), body_format="form")
        client.create_shortcut(URL, description="A & B + café", requires_ios26_ai=False, auto_submit=True)
        prepared, _, body = adapter.calls[0]
        self.assertEqual(prepared.headers["Content-Type"], "application/x-www-form-urlencoded")
        self.assertEqual(parse_qs(body), {"sharing_url": [URL], "description": ["A & B + café"],
                                         "requires_ios26_ai": ["false"], "auto_submit": ["true"]})

    def test_update_preserves_false_empty_strings_and_null(self):
        client, adapter = self.client(response(201, {"status": "pending", "replaced_pending": True}))
        result = client.update_shortcut(UUID, description="", requires_ios26_ai=False, clear_category=True,
                                        version="1.2.0", changelog="Changes", visibility="private")
        self.assertTrue(result["replaced_pending"])
        self.assertEqual(json.loads(adapter.calls[0][2]), {
            "description": "", "requires_ios26_ai": False, "category": None,
            "version": "1.2.0", "changelog": "Changes", "visibility": "private"})

    def test_form_clear_rejected_before_request(self):
        client, adapter = self.client(body_format="form")
        with self.assertRaisesRegex(ShortcutyAPIError, "requires --body-format json"):
            client.update_shortcut(UUID, clear_description=True)
        self.assertEqual(adapter.calls, [])

    def test_empty_update_rejected(self):
        client, adapter = self.client()
        with self.assertRaises(ShortcutyAPIError):
            client.update_shortcut(UUID)
        self.assertEqual(adapter.calls, [])

    def test_submit_200_and_202_are_bodiless_and_preserved(self):
        for status in (200, 202):
            with self.subTest(status=status):
                client, adapter = self.client(response(status, {"message": "Pending", "scan_queued": status == 200}))
                result = client.submit_shortcut(UUID)
                self.assertEqual(result["scan_queued"], status == 200)
                self.assertIsNone(adapter.calls[0][2])

    def test_pagination_query_and_response_preserved(self):
        body = {"shortcuts": [], "total": 21, "pages": 2, "current_page": 2}
        client, adapter = self.client(response(body=body))
        self.assertEqual(client.list_shortcuts(2, 20), body)
        self.assertEqual(parse_qs(urlsplit(adapter.calls[0][0].url).query), {"page": ["2"], "per_page": ["20"]})

    def test_invalid_page_rejected_without_request(self):
        client, adapter = self.client()
        for page, per_page in ((0, 20), (1, 0), (-1, 2)):
            with self.assertRaises(ShortcutyAPIError):
                client.list_shortcuts(page, per_page)
        self.assertEqual(adapter.calls, [])

    def test_error_status_retained_and_secret_redacted(self):
        for status in (400, 401, 403, 404, 413, 415, 500):
            with self.subTest(status=status):
                client, adapter = self.client(response(status, {"error": "Failure with Bearer " + KEY}))
                with self.assertRaises(ShortcutyAPIError) as raised:
                    client.submit_shortcut(UUID)
                self.assertEqual(raised.exception.status_code, status)
                self.assertIn("HTTP " + str(status), str(raised.exception))
                self.assertNotIn(KEY, str(raised.exception))
                self.assertEqual(len(adapter.calls), 1)

    def test_non_json_error_does_not_echo_server_html(self):
        client, _ = self.client(response(502, content=b"<html>private credential</html>"))
        with self.assertRaisesRegex(ShortcutyAPIError, "HTTP 502") as raised:
            client.get_categories()
        self.assertNotIn("private credential", str(raised.exception))

    def test_success_invalid_json_or_array_is_clear_error(self):
        for content in (b"<html>unexpected</html>", b"[]"):
            client, _ = self.client(response(content=content))
            with self.assertRaisesRegex(ShortcutyAPIError, "JSON"):
                client.get_categories()

    def test_timeout_or_connection_failure_not_retried_or_echoed(self):
        client, _ = self.client()
        for error in (requests.Timeout(KEY), requests.ConnectionError("Bearer " + KEY)):
            with patch.object(client.session, "request", side_effect=error) as send:
                with self.assertRaisesRegex(ShortcutyAPIError, "not retried") as raised:
                    client.create_shortcut(URL)
                self.assertNotIn(KEY, str(raised.exception))
                self.assertEqual(send.call_count, 1)

    def test_post_redirect_not_followed(self):
        client, adapter = self.client(response(307, headers={"Location": "https://example.invalid"}))
        with self.assertRaisesRegex(ShortcutyAPIError, "HTTP 307"):
            client.create_shortcut(URL)
        self.assertEqual(len(adapter.calls), 1)

    def test_gif_upload_uses_expected_multipart_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "screen.gif"
            image.write_bytes(b"GIF89a synthetic fixture")
            client, adapter = self.client(response(body={"screenshot": {"id": 1}}))
            client.upload_screenshot(UUID, str(image))
            prepared, _, body = adapter.calls[0]
            self.assertIn("multipart/form-data; boundary=", prepared.headers["Content-Type"])
            self.assertIn(b'name="file"; filename="screen.gif"', body)
            self.assertIn(UUID.encode(), body)
            self.assertIn(b'name="shortcut_id"', body)

    def test_mismatched_image_type_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "screen.gif"
            image.write_bytes(b"\x89PNG\r\n\x1a\n synthetic")
            with self.assertRaises(ShortcutyAPIError):
                validate_image_file(str(image))

    def test_url_validation_rejects_trailing_host_path_junk(self):
        for suffix in ("/extra", " bad", "@evil.invalid"):
            with self.assertRaises(ShortcutyAPIError):
                validate_icloud_url(URL + suffix)
        validate_icloud_url(URL + "?source=test#fragment")

    def test_nullable_fields_and_live_response_names_render(self):
        self.assertIn("Description:", format_shortcut({"description": None}))
        self.assertIn("private", format_shortcut({"description": "", "visibility": "private"}))
        self.assertIn("Version: 2.0", format_history({"changelog": [{"changes": {"new_version": "2.0"}}]}))
        self.assertIn("created", format_screenshot({"screenshot": {"created_at": "created"}}))
        self.assertIn("scan_queued: False", format_message({"message": "Pending", "scan_queued": False}))
        self.assertIn("Page 2/3", format_shortcut_list({"shortcuts": [{}], "total": 45, "pages": 3, "current_page": 2}))
