"""API client for Shortcuty Creator API."""

import math
import os
import re
import uuid as uuid_lib
import requests
from shortcuty_cli.http import ShortcutyAPIError, request
from typing import Optional, Dict, Any, List


BASE_URL = "https://shortcuty.app/api/v1"


def validate_image_file(file_path: str) -> None:
    """
    Validate PNG, JPEG, or GIF extension and magic bytes.
    
    Args:
        file_path: Path to the file to validate
        
    Raises:
        ShortcutyAPIError: If file is not a valid PNG or JPEG image
    """
    # Check file extension (case-insensitive)
    ext = os.path.splitext(file_path)[1].lower()
    valid_extensions = {'.png', '.jpg', '.jpeg', '.gif'}
    
    if ext not in valid_extensions:
        raise ShortcutyAPIError(
            f"Invalid file type. Expected PNG, JPEG, or GIF, got: {ext or 'no extension'}. "
            f"Supported extensions: .png, .jpg, .jpeg, .gif"
        )
    
    # Read and validate magic bytes (file signature)
    try:
        with open(file_path, "rb") as f:
            header = f.read(8)
            
        if len(header) < 3:
            raise ShortcutyAPIError(
                f"File is too small or corrupted. Expected PNG, JPEG, or GIF image."
            )
        
        # PNG magic bytes: 89 50 4E 47 0D 0A 1A 0A
        png_signature = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])
        # JPEG magic bytes: FF D8 FF
        jpeg_signature = bytes([0xFF, 0xD8, 0xFF])
        
        is_png = header[:8] == png_signature
        is_jpeg = header[:3] == jpeg_signature
        
        is_gif = header[:6] in (b"GIF87a", b"GIF89a")

        if not (is_png or is_jpeg or is_gif):
            detected_type = "unknown"
            if ext == '.png':
                detected_type = "not a valid PNG"
            elif ext in {'.jpg', '.jpeg'}:
                detected_type = "not a valid JPEG"
            
            raise ShortcutyAPIError(
                f"File type mismatch. File extension suggests {ext.upper()}, "
                f"but file signature indicates {detected_type}. "
                f"Please ensure the file is a valid PNG or JPEG image."
            )
        
        # Additional check: extension should match detected type
        if ext == '.png' and not is_png:
            raise ShortcutyAPIError(
                f"File extension is .png, but file signature indicates it's not a PNG image. "
                f"Please ensure the file is a valid PNG image."
            )
        elif ext == ".gif" and not is_gif:
            raise ShortcutyAPIError("File extension is .gif, but content is not a GIF image.")
        elif ext in {'.jpg', '.jpeg'} and not is_jpeg:
            raise ShortcutyAPIError(
                f"File extension is {ext}, but file signature indicates it's not a JPEG image. "
                f"Please ensure the file is a valid JPEG image."
            )
            
    except IOError as e:
        raise ShortcutyAPIError(f"Error reading file for validation: {str(e)}")


def validate_icloud_url(url: str) -> None:
    """
    Validate that a URL is a valid iCloud shortcuts sharing URL.
    
    Args:
        url: URL to validate
        
    Raises:
        ShortcutyAPIError: If URL is not a valid iCloud shortcuts URL
    """
    # Pattern for iCloud shortcuts URLs: https://www.icloud.com/shortcuts/... or https://icloud.com/shortcuts/...
    pattern = r'https://(www\.)?icloud\.com/shortcuts/[a-zA-Z0-9]+/?(?:[?#][^\s]*)?'
    
    if not re.fullmatch(pattern, url):
        raise ShortcutyAPIError(
            f"Invalid iCloud sharing URL format. Expected format: "
            f"https://www.icloud.com/shortcuts/... or https://icloud.com/shortcuts/..."
        )


def validate_uuid(uuid: str) -> None:
    """
    Validate that a string is a valid UUID format.
    
    Args:
        uuid: UUID string to validate
        
    Raises:
        ShortcutyAPIError: If UUID is not in valid format
    """
    try:
        uuid_lib.UUID(uuid)
    except (ValueError, AttributeError, TypeError):
        raise ShortcutyAPIError(
            f"Invalid UUID format: {uuid}. Expected format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
        )


class ShortcutyAPIClient:
    """Client for interacting with the Shortcuty Creator API."""
    
    def __init__(self, api_key: Optional[str] = None, timeout=60, body_format="json"):
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Timeout must be positive")
        if body_format not in ("json", "form"):
            raise ValueError("Body format must be json or form")
        self.api_key = api_key
        self.timeout = timeout
        self.body_format = body_format
        self.session = requests.Session()
        # Preserve explicit Bearer auth instead of silently substituting .netrc.
        self.session.auth = lambda prepared: prepared
        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})

    def close(self):
        self.session.close()

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        try:
            response = request(
                self.session, method, f"{BASE_URL}/{endpoint.lstrip('/')}",
                self.timeout, secret=self.api_key, **kwargs
            )
        except ShortcutyAPIError as error:
            if method.upper() not in ("GET", "HEAD") and error.status_code and error.status_code >= 500:
                raise ShortcutyAPIError(
                    str(error) + ". The request may already have saved data; check the result before repeating.",
                    status_code=error.status_code, code=error.code,
                ) from None
            raise
        try:
            try:
                body = response.json()
            except ValueError:
                raise ShortcutyAPIError(
                    f"HTTP {response.status_code}: Expected a JSON response. "
                    "Check the result before repeating a write."
                ) from None
            if not isinstance(body, dict):
                raise ShortcutyAPIError("Expected a JSON object response")
            return body
        finally:
            response.close()

    def _body(self, data):
        if self.body_format == "json":
            return {"json": data}
        if any(value is None for value in data.values()):
            raise ShortcutyAPIError("Clearing fields requires --body-format json; Form null is literal text")
        return {"data": {
            key: str(value).lower() if isinstance(value, bool) else value
            for key, value in data.items()
        }}

    def get_categories(self) -> List[str]:
        """Get list of all categories (public endpoint)."""
        response = self._request("GET", "/categories")
        return response.get("categories", [])
    
    def create_shortcut(
        self,
        sharing_url: str,
        description: Optional[str] = None,
        category: Optional[str] = None,
        requires_ios26_ai: Optional[bool] = None,
        updater_type: Optional[str] = None,
        auto_submit: Optional[bool] = None,
        visibility: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new shortcut."""
        validate_icloud_url(sharing_url)
        data = {"sharing_url": sharing_url}
        if description is not None:
            data["description"] = description
        if category is not None:
            data["category"] = category
        if requires_ios26_ai is not None:
            data["requires_ios26_ai"] = requires_ios26_ai
        if updater_type is not None:
            data["updater_type"] = updater_type
        if auto_submit is not None:
            data["auto_submit"] = auto_submit
        
        if visibility is not None:
            data["visibility"] = visibility
        return self._request("POST", "/shortcuts", **self._body(data))
    
    def list_shortcuts(self, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """List user's shortcuts with pagination."""
        if page < 1 or per_page < 1:
            raise ShortcutyAPIError("Page and per-page must be positive")
        params = {"page": page, "per_page": per_page}
        return self._request("GET", "/shortcuts/my", params=params)
    
    def get_shortcut(self, uuid: str) -> Dict[str, Any]:
        """Get shortcut details by UUID."""
        validate_uuid(uuid)
        return self._request("GET", f"/shortcuts/{uuid}")
    
    def get_shortcut_history(self, identifier: str) -> Dict[str, Any]:
        """Get version history for a shortcut."""
        validate_uuid(identifier)
        return self._request("GET", f"/shortcuts/{identifier}/history")
    
    def submit_shortcut(self, uuid: str) -> Dict[str, Any]:
        """Submit shortcut for review."""
        validate_uuid(uuid)
        return self._request("POST", f"/shortcuts/{uuid}/submit")
    
    def update_shortcut(
        self,
        uuid: str,
        description: Optional[str] = None,
        sharing_url: Optional[str] = None,
        category: Optional[str] = None,
        requires_ios26_ai: Optional[bool] = None,
        updater_type: Optional[str] = None,
        version: Optional[str] = None,
        changelog: Optional[str] = None,
        visibility: Optional[str] = None,
        clear_description: bool = False,
        clear_category: bool = False
    ) -> Dict[str, Any]:
        """Update an existing shortcut."""
        validate_uuid(uuid)
        if sharing_url is not None:
            validate_icloud_url(sharing_url)
        data = {}
        if description is not None:
            data["description"] = description
        if sharing_url is not None:
            data["sharing_url"] = sharing_url
        if category is not None:
            data["category"] = category
        if requires_ios26_ai is not None:
            data["requires_ios26_ai"] = requires_ios26_ai
        if updater_type is not None:
            data["updater_type"] = updater_type
        if version is not None:
            data["version"] = version
        if changelog is not None:
            data["changelog"] = changelog
        
        if visibility is not None:
            data["visibility"] = visibility
        if clear_description:
            data["description"] = None
        if clear_category:
            data["category"] = None
        if not data:
            raise ShortcutyAPIError("At least one update field must be provided")
        return self._request("POST", f"/shortcuts/{uuid}/update", **self._body(data))
    
    def upload_screenshot(self, uuid: str, file_path: str) -> Dict[str, Any]:
        """Upload a screenshot for a shortcut."""
        validate_uuid(uuid)
        validate_image_file(file_path)
        try:
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f)}
                data = {"shortcut_id": uuid}
                return self._request("POST", "/upload/screenshot", files=files, data=data)
        except FileNotFoundError:
            raise ShortcutyAPIError(f"File not found: {file_path}")
        except IOError as e:
            raise ShortcutyAPIError(f"Error reading file: {str(e)}")
    
    def delete_screenshot(self, shortcut_uuid: str, screenshot_id: int) -> Dict[str, Any]:
        """Delete a screenshot for a shortcut."""
        validate_uuid(shortcut_uuid)
        if screenshot_id < 1:
            raise ShortcutyAPIError("Screenshot ID must be positive")
        return self._request("DELETE", f"/shortcuts/{shortcut_uuid}/screenshots/{screenshot_id}")

