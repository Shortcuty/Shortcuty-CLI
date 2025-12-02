"""Output formatters for CLI responses."""

import json
from typing import Any, Dict, List


def format_json(data: Any) -> str:
    """Format data as JSON string."""
    return json.dumps(data, indent=2, ensure_ascii=False)


def format_categories(categories: List[str], json_output: bool = False) -> str:
    """Format categories list."""
    if json_output:
        return format_json({"categories": categories})
    
    if not categories:
        return "No categories found."
    
    return "\n".join(f"  • {cat}" for cat in categories)


def format_shortcut(shortcut: Dict[str, Any], json_output: bool = False) -> str:
    """Format a single shortcut."""
    if json_output:
        return format_json(shortcut)
    
    lines = [
        f"UUID: {shortcut.get('uuid', 'N/A')}",
        f"Name: {shortcut.get('name', 'N/A')}",
        f"Status: {shortcut.get('status', 'N/A')}",
        f"Category: {shortcut.get('category', 'N/A') or 'None'}",
        f"Description: {shortcut.get('description', 'N/A')[:100]}{'...' if len(shortcut.get('description', '')) > 100 else ''}",
        f"Version: {shortcut.get('version', 'N/A')}",
        f"Downloads: {shortcut.get('downloads', 0)}",
        f"Likes: {shortcut.get('likes_count', 0)}",
        f"Sharing URL: {shortcut.get('sharing_url', 'N/A')}",
        f"Requires iOS 26 AI: {shortcut.get('requires_ios26_ai', False)}",
        f"Updater Type: {shortcut.get('updater_type', 'N/A')}",
        f"Created: {shortcut.get('created_at', 'N/A')}",
        f"Updated: {shortcut.get('updated_at', 'N/A')}",
    ]
    
    if shortcut.get('rejection_reason'):
        lines.append(f"Rejection Reason: {shortcut['rejection_reason']}")
    
    return "\n".join(lines)


def format_shortcut_list(response: Dict[str, Any], json_output: bool = False) -> str:
    """Format list of shortcuts with pagination."""
    if json_output:
        return format_json(response)
    
    shortcuts = response.get("shortcuts", [])
    total = response.get("total", 0)
    pages = response.get("pages", 0)
    current_page = response.get("current_page", 1)
    
    if not shortcuts:
        return "No shortcuts found."
    
    lines = [f"Found {total} shortcut(s) (Page {current_page}/{pages})\n"]
    
    for shortcut in shortcuts:
        lines.append(f"  {shortcut.get('name', 'N/A')} ({shortcut.get('uuid', 'N/A')})")
        lines.append(f"    Status: {shortcut.get('status', 'N/A')}")
        lines.append(f"    Category: {shortcut.get('category', 'N/A') or 'None'}")
        lines.append("")
    
    return "\n".join(lines)


def format_shortcut_details(response: Dict[str, Any], json_output: bool = False) -> str:
    """Format detailed shortcut information."""
    if json_output:
        return format_json(response)
    
    shortcut = response.get("shortcut", {})
    comments = response.get("comments", [])
    screenshots = response.get("screenshots", [])
    latest_update = response.get("latest_update")
    
    lines = [format_shortcut(shortcut, json_output=False)]
    
    if comments:
        lines.append(f"\nComments ({len(comments)}):")
        for comment in comments[:5]:  # Show first 5
            lines.append(f"  • {comment}")
        if len(comments) > 5:
            lines.append(f"  ... and {len(comments) - 5} more")
    
    if screenshots:
        lines.append(f"\nScreenshots ({len(screenshots)}):")
        for screenshot in screenshots:
            if isinstance(screenshot, dict):
                lines.append(f"  • {screenshot.get('url', screenshot.get('filename', 'N/A'))}")
            else:
                lines.append(f"  • {screenshot}")
    
    if latest_update:
        lines.append(f"\nLatest Update:")
        if isinstance(latest_update, dict):
            lines.append(f"  {json.dumps(latest_update, indent=4)}")
        else:
            lines.append(f"  {latest_update}")
    
    return "\n".join(lines)


def format_history(response: Dict[str, Any], json_output: bool = False) -> str:
    """Format shortcut history."""
    if json_output:
        return format_json(response)
    
    changelog = response.get("changelog", [])
    shortcut_name = response.get("shortcut_name", "N/A")
    shortcut_uuid = response.get("shortcut_uuid", "N/A")
    
    lines = [
        f"History for: {shortcut_name} ({shortcut_uuid})",
        f"Total versions: {len(changelog)}\n"
    ]
    
    if not changelog:
        return "\n".join(lines) + "No history found."
    
    for entry in changelog:
        lines.append(f"Version {entry.get('version', 'N/A')} - {entry.get('date', 'N/A')}")
        lines.append(f"  Status: {entry.get('status', 'N/A')}")
        if entry.get('changelog'):
            lines.append(f"  Changelog: {entry['changelog']}")
        if entry.get('changes'):
            changes = entry['changes']
            if changes.get('name'):
                lines.append(f"  Name changed: {changes['name']}")
            if changes.get('new_version'):
                lines.append(f"  Version changed: {changes['new_version']}")
            if changes.get('old_sharing_url'):
                lines.append(f"  Previous URL: {changes['old_sharing_url']}")
        lines.append("")
    
    return "\n".join(lines)


def format_message(response: Dict[str, Any], json_output: bool = False) -> str:
    """Format simple message response."""
    if json_output:
        return format_json(response)
    
    message = response.get("message", "Success")
    if "update_id" in response:
        return f"{message} (Update ID: {response['update_id']})"
    return message


def format_screenshot(response: Dict[str, Any], json_output: bool = False) -> str:
    """Format screenshot upload response."""
    if json_output:
        return format_json(response)
    
    screenshot = response.get("screenshot", {})
    lines = [
        f"Screenshot uploaded successfully",
        f"  ID: {screenshot.get('id', 'N/A')}",
        f"  Filename: {screenshot.get('filename', 'N/A')}",
        f"  URL: {screenshot.get('url', 'N/A')}",
        f"  Uploaded: {screenshot.get('uploaded_at', 'N/A')}",
    ]
    return "\n".join(lines)

