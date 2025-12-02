# Shortcuty Creator API CLI

A command-line interface for managing shortcuts via the Shortcuty Creator API.

## Installation

```bash
pip install -e .
```

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

```bash
shortcuty create --sharing-url "https://www.icloud.com/shortcuts/abc123" \
  --description "My awesome shortcut" \
  --category "Productivity"
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
shortcuty update <uuid> --name "New Name" --description "New description"
```

### Upload Screenshot

```bash
shortcuty upload-screenshot <uuid> /path/to/screenshot.png
```

## JSON Output

Add `--json` flag to any command for JSON output (useful for scripting):

```bash
shortcuty list --json
```

## Getting Your API Key

Visit your Account Settings on [shortcuty.app](https://shortcuty.app) and create an API key in the API Key Management section.

