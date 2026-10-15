"""In-memory transport: tests never connect to the network."""

import json
from unittest import TestCase
from unittest.mock import patch

import requests
from requests.adapters import BaseAdapter


UUID = "123e4567-e89b-12d3-a456-426614174000"
URL = "https://www.icloud.com/shortcuts/SYNTHETIC123"
KEY = "synthetic-test-key-never-a-real-credential"


def response(status=200, body=None, headers=None, content=None):
    result = requests.Response()
    result.status_code = status
    result._content = content if content is not None else json.dumps(body or {}).encode()
    result._content_consumed = True
    result.headers.update(headers or {"Content-Type": "application/json"})
    return result


class MemoryAdapter(BaseAdapter):
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def send(self, prepared, **kwargs):
        body = prepared.body
        if hasattr(body, "read"):
            body = b"".join(iter(lambda: body.read(1024), b""))
        self.calls.append((prepared, kwargs, body))
        if not self.responses:
            raise AssertionError("Unexpected HTTP request")
        result = self.responses.pop(0)
        result.request = prepared
        return result

    def close(self):
        pass


class OfflineTest(TestCase):
    def setUp(self):
        # A missed stub must fail instead of touching a service or local credentials.
        self.guard = patch("socket.socket.connect", side_effect=AssertionError("Network forbidden in tests"))
        self.guard.start()
        self.addCleanup(self.guard.stop)
        self.environment = patch.dict("os.environ", {}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)


def session_for(*responses):
    session = requests.Session()
    session.trust_env = False
    adapter = MemoryAdapter(*responses)
    session.mount("https://", adapter)
    return session, adapter
