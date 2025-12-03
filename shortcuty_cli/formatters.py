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
    screenshots = response.get("screenshots", [])
    latest_update = response.get("latest_update")
    
    lines = [format_shortcut(shortcut, json_output=False)]
    
    if screenshots:
        lines.append(f"\nScreenshots ({len(screenshots)}):")
        for screenshot in screenshots:
            if isinstance(screenshot, dict):
                url = screenshot.get('url', screenshot.get('filename', 'N/A'))
                order = screenshot.get('order', '')
                screenshot_id = screenshot.get('id', '')
                if order:
                    lines.append(f"  [{order}] {url} (ID: {screenshot_id})")
                else:
                    lines.append(f"  • {url} (ID: {screenshot_id})")
            else:
                lines.append(f"  • {screenshot}")
    
    if latest_update:
        lines.append(f"\nLatest Update:")
        if isinstance(latest_update, dict):
            update_lines = []
            if latest_update.get('new_version'):
                update_lines.append(f"  Version: {latest_update['new_version']}")
            if latest_update.get('changelog'):
                update_lines.append(f"  Changelog: {latest_update['changelog']}")
            if latest_update.get('status'):
                update_lines.append(f"  Status: {latest_update['status']}")
            if latest_update.get('approved_at'):
                update_lines.append(f"  Approved: {latest_update['approved_at']}")
            if update_lines:
                lines.extend(update_lines)
            else:
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
        version = entry.get('version', 'N/A')
        date = entry.get('date', 'N/A')
        status = entry.get('status', 'N/A')
        
        lines.append(f"Version {version} - {date}")
        lines.append(f"  Status: {status}")
        
        if entry.get('changelog'):
            lines.append(f"  Changelog: {entry['changelog']}")
        
        if entry.get('sharing_url'):
            lines.append(f"  Sharing URL: {entry['sharing_url']}")
        
        if entry.get('changes'):
            changes = entry['changes']
            change_items = []
            if changes.get('name'):
                change_items.append(f"Name: {changes['name']}")
            if changes.get('description'):
                change_items.append(f"Description: {changes['description'][:50]}...")
            if changes.get('category'):
                change_items.append(f"Category: {changes['category']}")
            if changes.get('requires_ios26_ai') is not None:
                change_items.append(f"Requires iOS 26 AI: {changes['requires_ios26_ai']}")
            if changes.get('updater_type'):
                change_items.append(f"Updater Type: {changes['updater_type']}")
            if changes.get('new_version'):
                change_items.append(f"Version: {changes['new_version']}")
            
            if change_items:
                lines.append(f"  Changes: {', '.join(change_items)}")
        
        if entry.get('rejection_reason'):
            lines.append(f"  Rejection Reason: {entry['rejection_reason']}")
        
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


def format_delete_screenshot(response: Dict[str, Any], json_output: bool = False) -> str:
    """Format screenshot deletion response."""
    if json_output:
        return format_json(response)
    
    message = response.get("message", "Screenshot deleted successfully")
    return message

