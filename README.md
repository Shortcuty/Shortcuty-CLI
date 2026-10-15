# Shortcuty Creator CLI

A command-line interface for managing shortcuts via the Shortcuty Creator API v1.

📚 **API Documentation:** [Shortcuty API Docs](https://github.com/Shortcuty/ShortcutyDocs)

## Features

- Create, update, and manage shortcuts
- Upload and delete screenshots
- View shortcut history and changelogs
- List and filter your shortcuts
- JSON output support for scripting
- Sign local unsigned `.shortcut` files without an API key

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

1. **Environment variable**: `SHORTCUTY_API_KEY`

2. **Command-line flag**: `--api-key`

The CLI checks these in order: CLI flag > Environment variable.

Prefer the environment variable: command-line keys may be saved in shell history
or visible in process listings. The CLI does not save API keys in a config file.
`~/.shortcuty/last_update_check.json` contains only an update-check timestamp.
Categories and signing do not require an API key.

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

Use `--visibility private` to create a private shortcut. The default is public.

### List Your Shortcuts

```bash
shortcuty list --page 1 --per-page 20
```

Page numbers and page sizes must be positive.

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

Set a boolean to false or clear an optional field explicitly:

```bash
shortcuty update <uuid> --no-requires-ios26-ai --visibility private
shortcuty update <uuid> --clear-description --clear-category
```

`--clear-description` and `--clear-category` send JSON `null`; they require the
default JSON body format. An empty string can also be sent with `--description ""`.
Use either a field value or its clear option in one command.

A new update replaces the entire pending proposal. Include all unapproved changes
and release notes you want to keep. Successful submission or an update accepted
for review does not mean approval: inspect the message, `status`, and `scan_queued`,
then use `get` or `history` to check progress.

### Upload Screenshot

```bash
shortcuty upload-screenshot <uuid> /path/to/screenshot.png
```

PNG, JPEG, and GIF files are supported. The API allows at most five screenshots.

### Delete Screenshot

```bash
shortcuty delete-screenshot <uuid> <screenshot_id>
```

### Sign a Local Shortcut

```bash
shortcuty sign "My Shortcut.shortcut"
shortcuty sign "My Shortcut.shortcut" --output "Signed/My Shortcut.shortcut"
shortcuty sign "My Shortcut.shortcut" --output "result.shortcut" --force
shortcuty --json sign "My Shortcut.shortcut" --timeout 900
```

Sign an unsigned `.shortcut` file with the [Shortcuty signing service](https://sign.shortcuty.app).
No API key is required. The signed file is saved in the current directory using
the server's suggested filename.

| Option | Purpose |
|---|---|
| `--output PATH`, `-o PATH` | Choose an output path; its parent directory must exist. |
| `--force` | Allow overwriting the output file. |
| `--timeout SECONDS` | Signing read timeout; default: **300 seconds**. |

**Overwrite warning:** `--force` can replace an existing file, including the input.

See the [Signing API documentation](https://github.com/Shortcuty/Signing-Server-API-Documentation)
for API details.

### Check for Updates

Check if a newer version of the CLI is available:

```bash
shortcuty check-updates
```

### Update CLI

Install the latest CLI from GitHub `main`:

```bash
shortcuty cli-update
```

## Global Options

Global options appear before the command name. `shortcuty --version` displays
the installed CLI version; `shortcuty update --version` sets a shortcut version.

### Request Body Format

Create and update default to JSON. URL-encoded Form uses the same field names:

```bash
shortcuty --body-format form update <uuid> --version "1.2.0" --changelog "Bug fixes"
```

### Timeouts and Errors

```bash
shortcuty --timeout 120 list --page 2 --per-page 20
```

Creator API commands use a **60-second** read timeout. Set `--timeout` before
the command to change it. Signing has its own [timeout option](#sign-a-local-shortcut).

Errors go to stderr and return a nonzero exit code. After a timeout or server
error, check the result before trying a write again: use `list` after creation,
`get <uuid>` after submission, and `history <uuid>` after an update.

### Skip Update Check

Disable automatic update checks for a command:

```bash
shortcuty --no-check-updates list
```

Automatic checks run after successful human-readable Creator commands. Help,
version, JSON output, and signing skip them. Notifications go to stderr.

## JSON Output

Add `--json` flag to any command for JSON output (useful for scripting):

```bash
shortcuty --json list
shortcuty --json get <uuid>
shortcuty --json categories
```

**Note:** The `--json` flag must be placed before the command name.

## Getting Your API Key

Visit your Account Settings on [browse.shortcuty.app](https://browse.shortcuty.app) and create an API key in the API Key Management section.

## Development and Tests

```bash
python -m pip install -e .
python -m unittest discover -v
```

Tests use synthetic workflows, fake HTTP responses, and a network guard. They do
not need an account, real API key, Apple signer, or service mutations. CI covers
Python 3.8 and 3.12, including Windows and macOS.

## Documentation

For detailed API documentation, see the [Shortcuty API Documentation](https://github.com/Shortcuty/ShortcutyDocs).

