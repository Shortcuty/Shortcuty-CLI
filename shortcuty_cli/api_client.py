"""API client for Shortcuty Creator API."""

import os
import re
import uuid as uuid_lib
import requests
from typing import Optional, Dict, Any, List


BASE_URL = "https://shortcuty.app/api/v1"


class ShortcutyAPIError(Exception):
    """Base exception for API errors."""
    pass


def validate_image_file(file_path: str) -> None:
    """
    Validate that a file is a PNG or JPEG image by checking extension and magic bytes.
    
    Args:
        file_path: Path to the file to validate
        
    Raises:
        ShortcutyAPIError: If file is not a valid PNG or JPEG image
    """
    # Check file extension (case-insensitive)
    ext = os.path.splitext(file_path)[1].lower()
    valid_extensions = {'.png', '.jpg', '.jpeg'}
    
    if ext not in valid_extensions:
        raise ShortcutyAPIError(
            f"Invalid file type. Expected PNG or JPEG, got: {ext or 'no extension'}. "
            f"Supported extensions: .png, .jpg, .jpeg"
        )
    
    # Read and validate magic bytes (file signature)
    try:
        with open(file_path, "rb") as f:
            header = f.read(8)
            
        if len(header) < 3:
            raise ShortcutyAPIError(
                f"File is too small or corrupted. Expected PNG or JPEG image."
            )
        
        # PNG magic bytes: 89 50 4E 47 0D 0A 1A 0A
        png_signature = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])
        # JPEG magic bytes: FF D8 FF
        jpeg_signature = bytes([0xFF, 0xD8, 0xFF])
        
        is_png = header[:8] == png_signature
        is_jpeg = header[:3] == jpeg_signature
        
        if not (is_png or is_jpeg):
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
    pattern = r'^https://(www\.)?icloud\.com/shortcuts/[a-zA-Z0-9]+'
    
    if not re.match(pattern, url):
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
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize API client.
        
        Args:
            api_key: API key for authentication (optional for public endpoints)
        """
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({
                "Authorization": f"Bearer {api_key}"
            })
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make HTTP request to API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            **kwargs: Additional arguments for requests
            
        Returns:
            dict: JSON response
            
        Raises:
            ShortcutyAPIError: If request fails
        """
        url = f"{BASE_URL}/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_msg = f"API request failed: {e.response.status_code}"
            try:
                error_data = e.response.json()
                if "message" in error_data:
                    error_msg = error_data["message"]
                elif "error" in error_data:
                    error_msg = error_data["error"]
            except (ValueError, KeyError, requests.exceptions.JSONDecodeError):
                # If JSON parsing fails, use default error message
                pass
            raise ShortcutyAPIError(error_msg) from e
        except requests.exceptions.RequestException as e:
            raise ShortcutyAPIError(f"Request failed: {str(e)}") from e
    
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
        submit: Optional[bool] = None
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
        if submit is not None:
            data["submit"] = submit
        
        return self._request("POST", "/shortcuts", json=data)
    
    def list_shortcuts(self, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """List user's shortcuts with pagination."""
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
        name: Optional[str] = None,
        description: Optional[str] = None,
        sharing_url: Optional[str] = None,
        category: Optional[str] = None,
        requires_ios26_ai: Optional[bool] = None,
        updater_type: Optional[str] = None,
        new_version: Optional[str] = None,
        changelog: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update an existing shortcut."""
        validate_uuid(uuid)
        if sharing_url is not None:
            validate_icloud_url(sharing_url)
        data = {}
        if name is not None:
            data["name"] = name
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
        if new_version is not None:
            data["new_version"] = new_version
        if changelog is not None:
            data["changelog"] = changelog
        
        return self._request("POST", f"/shortcuts/{uuid}/update", json=data)
    
    def upload_screenshot(self, uuid: str, file_path: str) -> Dict[str, Any]:
        """Upload a screenshot for a shortcut."""
        validate_uuid(uuid)
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
        return self._request("DELETE", f"/shortcuts/{shortcut_uuid}/screenshots/{screenshot_id}")

