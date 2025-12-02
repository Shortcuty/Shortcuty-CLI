"""Configuration management for API key."""

import json
import os
from pathlib import Path


CONFIG_DIR = Path.home() / ".shortcuty"
CONFIG_FILE = CONFIG_DIR / "config.json"
ENV_VAR = "SHORTCUTY_API_KEY"


def get_api_key(cli_api_key=None):
    """
    Get API key from various sources in priority order:
    1. CLI argument
    2. Environment variable
    3. Config file
    
    Args:
        cli_api_key: API key provided via CLI flag
        
    Returns:
        str: API key or None if not found
    """
    if cli_api_key:
        return cli_api_key
    
    env_key = os.getenv(ENV_VAR)
    if env_key:
        return env_key
    
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                return config.get("api_key")
        except (json.JSONDecodeError, IOError):
            pass
    
    return None


def save_api_key(api_key):
    """
    Save API key to config file.
    
    Args:
        api_key: API key to save
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        config = {"api_key": api_key}
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        return True
    except IOError:
        return False

