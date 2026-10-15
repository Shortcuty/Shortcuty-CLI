"""Bounded HTTP calls shared by the creator and signing clients."""

import re

import requests


class ShortcutyAPIError(Exception):
    """A safe, user-facing error with optional HTTP status and server code."""

    def __init__(self, message, status_code=None, code=None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code


def safe_message(value, secret=None):
    """Never echo a known credential or an Authorization value."""
    text = str(value)
    if secret:
        text = text.replace(secret, "[REDACTED]")
    text = re.sub(r"(?i)bearer\s+[^\s\"'<>]+", "Bearer [REDACTED]", text)
    return " ".join(text.split())[:500]


def response_error(response, secret=None):
    """Decode both public-v1 string errors and signer structured errors."""
    status = response.status_code
    message, code = "Request failed", None
    try:
        body = response.json()
        if isinstance(body, dict):
            error = body.get("error") or body.get("message")
            if isinstance(error, dict):
                code = error.get("code")
                message = error.get("message") or message
            elif isinstance(error, str):
                message = error
    except ValueError:
        pass  # Proxy HTML and raw responses may contain sensitive information.
    if status == 413:
        message = "Upload exceeds the server or proxy size limit"
    if status in (429, 503) and response.headers.get("Retry-After"):
        message += "; Retry-After: " + safe_message(response.headers["Retry-After"], secret)
    return ShortcutyAPIError(
        "HTTP {}{}: {}".format(
            status, " ({})".format(safe_message(code, secret)) if code else "",
            safe_message(message, secret),
        ), status_code=status, code=code,
    )


def request(session, method, url, timeout, secret=None, **kwargs):
    """One attempt only: redirects and automatic retries could repeat a write."""
    try:
        response = session.request(
            method, url, timeout=(10, timeout), allow_redirects=False, **kwargs
        )
    except requests.exceptions.Timeout:
        raise ShortcutyAPIError(
            "Request timed out. It was not retried; check the result before repeating a write."
        ) from None
    except requests.exceptions.RequestException:
        raise ShortcutyAPIError(
            "Network request failed. It was not retried; check the result before repeating a write."
        ) from None
    if not 200 <= response.status_code < 300:
        try:
            raise response_error(response, secret)
        finally:
            response.close()
    return response
