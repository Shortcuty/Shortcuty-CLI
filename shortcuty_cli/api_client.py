"""API client for Shortcuty Creator API."""

import os
import requests
from typing import Optional, Dict, Any, List


BASE_URL = "https://shortcuty.app/api/v1"


class ShortcutyAPIError(Exception):
    """Base exception for API errors."""
    pass


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
            except:
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
        return self._request("GET", f"/shortcuts/{uuid}")
    
    def get_shortcut_history(self, identifier: str) -> Dict[str, Any]:
        """Get version history for a shortcut."""
        return self._request("GET", f"/shortcuts/{identifier}/history")
    
    def submit_shortcut(self, uuid: str) -> Dict[str, Any]:
        """Submit shortcut for review."""
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
        return self._request("DELETE", f"/shortcuts/{shortcut_uuid}/screenshots/{screenshot_id}")

