"""Configuration management for API key."""

import os
from pathlib import Path


CONFIG_DIR = Path.home() / ".shortcuty"
ENV_VAR = "SHORTCUTY_API_KEY"


def get_api_key(cli_api_key=None):
    """
    Get API key from various sources in priority order:
    1. CLI argument
    2. Environment variable
    
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
    
    return None

