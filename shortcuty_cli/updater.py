"""Auto-update functionality for Shortcuty CLI."""

import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

import requests
from packaging import version

from shortcuty_cli import __version__
from shortcuty_cli.config import CONFIG_DIR


CACHE_FILE = CONFIG_DIR / "last_update_check.json"
VERSION_FILE_URL = "https://raw.githubusercontent.com/Shortcuty/Shortcuty-CLI/main/VERSION"
GITHUB_INSTALL_URL = "git+https://github.com/Shortcuty/Shortcuty-CLI.git"
CACHE_DURATION_HOURS = 24


def get_current_version() -> str:
    """Get the current installed version."""
    return __version__


def should_check_updates() -> bool:
    """
    Check if enough time has passed since last update check.
    
    Returns:
        bool: True if should check for updates, False otherwise
    """
    if not CACHE_FILE.exists():
        return True
    
    try:
        with open(CACHE_FILE, "r") as f:
            cache_data = json.load(f)
            last_check = cache_data.get("last_check")
            if not last_check:
                return True
            
            last_check_time = datetime.fromisoformat(last_check)
            time_since_check = datetime.now() - last_check_time
            
            return time_since_check >= timedelta(hours=CACHE_DURATION_HOURS)
    except (json.JSONDecodeError, IOError, ValueError, KeyError):
        # If cache is invalid, regenerate it
        return True


def update_cache_timestamp() -> None:
    """Update the cache file with current timestamp."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        cache_data = {
            "last_check": datetime.now().isoformat()
        }
        with open(CACHE_FILE, "w") as f:
            json.dump(cache_data, f, indent=2)
    except IOError:
        # Silently fail if we can't write cache
        pass


def check_for_updates() -> Optional[Dict[str, Any]]:
    """
    Check for available updates by fetching version from text file.
    
    Returns:
        dict with 'version' and 'current_version' keys if update available, None otherwise
    """
    try:
        response = requests.get(VERSION_FILE_URL, timeout=5)
        response.raise_for_status()
        
        # Get version from text file (strip whitespace and 'v' prefix if present)
        latest_version = response.text.strip().lstrip("v")
        current_version = get_current_version()
        
        # Compare versions
        try:
            if version.parse(latest_version) > version.parse(current_version):
                return {
                    "version": latest_version,
                    "current_version": current_version
                }
        except (ValueError, version.InvalidVersion):
            # If version parsing fails, skip update check
            return None
        
        return None
    except (requests.exceptions.RequestException, ValueError):
        # Network errors or invalid version format - fail silently
        return None


def install_update() -> bool:
    """
    Install the latest version from GitHub.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        result = subprocess.run(
            ["pip", "install", "--upgrade", GITHUB_INSTALL_URL],
            capture_output=True,
            text=True,
            timeout=120
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def prompt_for_update(update_info: Dict[str, Any]) -> bool:
    """
    Prompt user to confirm and install update.
    
    Args:
        update_info: Dictionary with update information
        
    Returns:
        bool: True if update was installed, False otherwise
    """
    current = update_info.get("current_version", "unknown")
    latest = update_info.get("version", "unknown")
    
    print(f"\n{'='*60}")
    print(f"Update available: {current} -> {latest}")
    print(f"{'='*60}")
    
    try:
        response = input("\nWould you like to update now? [y/N]: ").strip().lower()
        if response in ('y', 'yes'):
            print("\nInstalling update...")
            if install_update():
                print(f"Successfully updated to version {latest}!")
                print("Please restart the CLI to use the new version.")
                return True
            else:
                print("Update installation failed. Please update manually:")
                print(f"  pip install --upgrade {GITHUB_INSTALL_URL}")
                return False
        else:
            print("Update skipped.")
            return False
    except (KeyboardInterrupt, EOFError):
        print("\nUpdate cancelled.")
        return False

