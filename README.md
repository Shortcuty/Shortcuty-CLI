# Shortcuty Creator CLI

A command-line interface for managing shortcuts via the Shortcuty Creator API v1.

📚 **API Documentation:** [Shortcuty API Docs](https://github.com/Shortcuty/ShortcutyDocs)

## Features

- Create, update, and manage shortcuts
- Upload and delete screenshots
- View shortcut history and changelogs
- List and filter your shortcuts
- JSON output support for scripting

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

## Installation

### Install from Git Repository

```bash
pip install git+https://github.com/Shortcuty/Shortcuty-CLI.git
```

### Verify Installation

After installation, verify the CLI is working:

```bash
shortcuty --help
```

You should see the CLI help menu. If you get a "command not found" error, make sure the Python scripts directory is in your PATH.

## Configuration

The CLI supports multiple ways to provide your API key:

1. **Config file** (recommended): `~/.shortcuty/config.json`
   ```json
   {
     "api_key": "your-api-key-here"
   }
   ```

2. **Environment variable**: `SHORTCUTY_API_KEY`

3. **Command-line flag**: `--api-key`

The CLI checks these in order: CLI flag > Environment variable > Config file.

## Usage

### List Categories (Public)

```bash
shortcuty categories
```

### Create a Shortcut

Create a draft shortcut:

```bash
shortcuty create --sharing-url "https://www.icloud.com/shortcuts/abc123" \
  --description "My awesome shortcut" \
  --category "Productivity"
```

Create and immediately submit for review:

```bash
shortcuty create --sharing-url "https://www.icloud.com/shortcuts/abc123" \
  --description "My awesome shortcut" \
  --category "Productivity" \
  --auto-submit
```

Additional options:

```bash
shortcuty create --sharing-url "https://www.icloud.com/shortcuts/abc123" \
  --description "My awesome shortcut" \
  --category "Productivity" \
  --requires-ios26-ai \
  --updater-type shortcuty \
  --auto-submit
```

### List Your Shortcuts

```bash
shortcuty list --page 1 --per-page 20
```

### Get Shortcut Details

```bash
shortcuty get <uuid>
```

### Get Shortcut History

```bash
shortcuty history <uuid>
```

### Submit Shortcut for Review

```bash
shortcuty submit <uuid>
```

### Update Shortcut

```bash
shortcuty update <uuid> --description "New description"
```

You can update multiple fields at once:

```bash
shortcuty update <uuid> \
  --description "Updated description" \
  --sharing-url "https://www.icloud.com/shortcuts/new-url" \
  --category "Productivity" \
  --version "2.0" \
  --changelog "What's new in this version"
```

### Upload Screenshot

```bash
shortcuty upload-screenshot <uuid> /path/to/screenshot.png
```

### Delete Screenshot

```bash
shortcuty delete-screenshot <uuid> <screenshot_id>
```

### Check for Updates

Check if a newer version of the CLI is available:

```bash
shortcuty check-updates
```

### Update CLI

Update to the latest version of the CLI:

```bash
shortcuty cli-update
```

## Global Options

### Skip Update Check

Disable automatic update checks for a command:

```bash
shortcuty --no-check-updates list
```

## JSON Output

Add `--json` flag to any command for JSON output (useful for scripting):

```bash
shortcuty --json list
shortcuty --json get <uuid>
shortcuty --json categories
```

**Note:** The `--json` flag must be placed before the command name.

## Getting Your API Key

Visit your Account Settings on [shortcuty.app](https://shortcuty.app) and create an API key in the API Key Management section.

## Documentation

For detailed API documentation, see the [Shortcuty API Documentation](https://github.com/Shortcuty/ShortcutyDocs).

