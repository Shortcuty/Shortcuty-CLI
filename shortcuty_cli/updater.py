"""Auto-update functionality for Shortcuty CLI."""

import ast
import json
import sys
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

import requests
from packaging import version

from shortcuty_cli import __version__
from shortcuty_cli.http import ShortcutyAPIError
from shortcuty_cli.config import CONFIG_DIR


CACHE_FILE = CONFIG_DIR / "last_update_check.json"
VERSION_FILE_URL = "https://raw.githubusercontent.com/Shortcuty/Shortcuty-CLI/main/shortcuty_cli/__init__.py"
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
            
            return time_since_check < timedelta(0) or time_since_check >= timedelta(hours=CACHE_DURATION_HOURS)
    except (json.JSONDecodeError, IOError, ValueError, KeyError, TypeError, AttributeError):
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
    Read version metadata from repository source without executing that source.
    
    Returns:
        dict with 'version' and 'current_version' keys if update available, None otherwise
    """
    try:
        response = requests.get(VERSION_FILE_URL, timeout=(5, 5), allow_redirects=False)
        try:
            if response.status_code != 200:
                raise ShortcutyAPIError(f"Update check failed: HTTP {response.status_code}")
            if len(response.content) > 65536:
                raise ValueError("Version source too large")
            module = ast.parse(response.text)
            latest_version = None
            for node in module.body:
                if (isinstance(node, ast.Assign)
                        and any(isinstance(target, ast.Name) and target.id == "__version__"
                                for target in node.targets)):
                    latest_version = ast.literal_eval(node.value)
            if not isinstance(latest_version, str):
                raise ValueError("Missing version")
            latest = version.Version(latest_version)
            current_version = get_current_version()
            if latest > version.Version(current_version):
                return {"version": str(latest), "current_version": current_version}
            return None
        finally:
            response.close()
    except requests.exceptions.RequestException:
        raise ShortcutyAPIError("Unable to check for updates: network request failed") from None
    except (ValueError, SyntaxError, TypeError):
        raise ShortcutyAPIError("Unable to check for updates: invalid version metadata") from None


def install_update() -> bool:
    """
    Install the latest version from GitHub.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", GITHUB_INSTALL_URL],
            capture_output=True,
            text=True,
            timeout=120
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def show_update_notification(update_info: Dict[str, Any]) -> None:
    """
    Show a non-blocking notification about available update.
    
    Args:
        update_info: Dictionary with update information
    """
    current = update_info.get("current_version", "unknown")
    latest = update_info.get("version", "unknown")
    
    print(f"\nUpdate available: {current} -> {latest}", file=sys.stderr)
    print("   Run 'shortcuty cli-update' to install it\n", file=sys.stderr)


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

