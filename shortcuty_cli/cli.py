"""Command-line interface for Shortcuty Creator API."""

import functools
import click
from shortcuty_cli.api_client import ShortcutyAPIClient, ShortcutyAPIError, validate_image_file
from shortcuty_cli.config import get_api_key
from shortcuty_cli.updater import (
    check_for_updates,
    should_check_updates,
    update_cache_timestamp,
    show_update_notification,
    get_current_version,
    install_update,
)
from shortcuty_cli.formatters import (
    format_categories,
    format_shortcut,
    format_shortcut_list,
    format_shortcut_details,
    format_history,
    format_message,
    format_screenshot,
    format_delete_screenshot,
)


def require_api_key(f):
    """Decorator to require API key for a command."""
    @functools.wraps(f)
    def wrapper(ctx, *args, **kwargs):
        if not ctx.obj["api_key"]:
            click.echo("Error: API key required. Use --api-key or set SHORTCUTY_API_KEY.", err=True)
            ctx.exit(1)
        return f(ctx, *args, **kwargs)
    return wrapper


@click.group()
@click.option(
    "--api-key",
    envvar="SHORTCUTY_API_KEY",
    help="API key for authentication (can also use SHORTCUTY_API_KEY env var or config file)",
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Output results as JSON",
)
@click.option(
    "--no-check-updates",
    "no_check_updates",
    is_flag=True,
    help="Skip automatic update check",
)
@click.pass_context
def cli(ctx, api_key, json_output, no_check_updates):
    """Shortcuty Creator API CLI - Manage shortcuts programmatically."""
    ctx.ensure_object(dict)
    api_key = get_api_key(api_key)
    ctx.obj["api_key"] = api_key
    ctx.obj["json_output"] = json_output
    ctx.obj["client"] = ShortcutyAPIClient(api_key=api_key)
    
    # Check for updates (non-blocking, with error handling)
    if not no_check_updates and should_check_updates():
        try:
            update_info = check_for_updates()
            if update_info:
                show_update_notification(update_info)
            update_cache_timestamp()
        except Exception:
            # Silently fail - don't interrupt CLI usage if update check fails
            pass


@cli.command()
@click.pass_context
def categories(ctx):
    """List all available categories (public endpoint)."""
    try:
        client = ShortcutyAPIClient()  # No auth needed for public endpoint
        categories_list = client.get_categories()
        click.echo(format_categories(categories_list, ctx.obj["json_output"]))
    except ShortcutyAPIError as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.option("--sharing-url", required=True, help="iCloud sharing URL")
@click.option("--description", help="Shortcut description")
@click.option("--category", help="Category name")
@click.option("--requires-ios26-ai", is_flag=True, help="Requires iOS 26 AI features")
@click.option(
    "--updater-type",
    type=click.Choice(["shortcuty", "third_party", "none"], case_sensitive=False),
    help="Updater type",
)
@click.option("--auto-submit", is_flag=True, help="Submit for review immediately")
@click.pass_context
@require_api_key
def create(ctx, sharing_url, description, category, requires_ios26_ai, updater_type, auto_submit):
    """Create a new shortcut."""
    try:
        client = ctx.obj["client"]
        response = client.create_shortcut(
            sharing_url=sharing_url,
            description=description,
            category=category,
            requires_ios26_ai=requires_ios26_ai if requires_ios26_ai else None,
            updater_type=updater_type,
            auto_submit=auto_submit if auto_submit else None,
        )
        shortcut = response.get("shortcut", {})
        click.echo(format_shortcut(shortcut, ctx.obj["json_output"]))
    except ShortcutyAPIError as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.option("--page", type=int, default=1, help="Page number")
@click.option("--per-page", type=int, default=20, help="Items per page")
@click.pass_context
@require_api_key
def list(ctx, page, per_page):
    """List your shortcuts."""
    try:
        client = ctx.obj["client"]
        response = client.list_shortcuts(page=page, per_page=per_page)
        click.echo(format_shortcut_list(response, ctx.obj["json_output"]))
    except ShortcutyAPIError as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.argument("uuid")
@click.pass_context
@require_api_key
def get(ctx, uuid):
    """Get shortcut details by UUID."""
    try:
        client = ctx.obj["client"]
        response = client.get_shortcut(uuid)
        click.echo(format_shortcut_details(response, ctx.obj["json_output"]))
    except ShortcutyAPIError as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.argument("uuid")
@click.pass_context
@require_api_key
def history(ctx, uuid):
    """Get version history for a shortcut."""
    try:
        client = ctx.obj["client"]
        response = client.get_shortcut_history(uuid)
        click.echo(format_history(response, ctx.obj["json_output"]))
    except ShortcutyAPIError as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.argument("uuid")
@click.pass_context
@require_api_key
def submit(ctx, uuid):
    """Submit shortcut for review."""
    try:
        client = ctx.obj["client"]
        response = client.submit_shortcut(uuid)
        click.echo(format_message(response, ctx.obj["json_output"]))
    except ShortcutyAPIError as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.argument("uuid")
@click.option("--description", help="Shortcut description")
@click.option("--sharing-url", help="iCloud sharing URL")
@click.option("--category", help="Category name")
@click.option("--requires-ios26-ai", is_flag=True, help="Requires iOS 26 AI features")
@click.option(
    "--updater-type",
    type=click.Choice(["shortcuty", "third_party", "none"], case_sensitive=False),
    help="Updater type",
)
@click.option("--version", help="Version string (e.g., '2.0')")
@click.option("--changelog", help="Changelog text")
@click.pass_context
@require_api_key
def update(
    ctx,
    uuid,
    description,
    sharing_url,
    category,
    requires_ios26_ai,
    updater_type,
    version,
    changelog,
):
    """Update an existing shortcut."""
    if not any([description, sharing_url, category, requires_ios26_ai, updater_type, version, changelog]):
        click.echo("Error: At least one update field must be provided.", err=True)
        ctx.exit(1)
    
    try:
        client = ctx.obj["client"]
        response = client.update_shortcut(
            uuid=uuid,
            description=description,
            sharing_url=sharing_url,
            category=category,
            requires_ios26_ai=requires_ios26_ai if requires_ios26_ai else None,
            updater_type=updater_type,
            version=version,
            changelog=changelog,
        )
        click.echo(format_message(response, ctx.obj["json_output"]))
    except ShortcutyAPIError as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.argument("uuid")
@click.argument("file", type=click.Path(exists=True, readable=True))
@click.pass_context
@require_api_key
def upload_screenshot(ctx, uuid, file):
    """Upload a screenshot for a shortcut."""
    try:
        # Validate file type before uploading
        validate_image_file(file)
        client = ctx.obj["client"]
        response = client.upload_screenshot(uuid, file)
        click.echo(format_screenshot(response, ctx.obj["json_output"]))
    except ShortcutyAPIError as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.argument("uuid")
@click.argument("screenshot_id", type=int)
@click.pass_context
@require_api_key
def delete_screenshot(ctx, uuid, screenshot_id):
    """Delete a screenshot for a shortcut."""
    try:
        client = ctx.obj["client"]
        response = client.delete_screenshot(uuid, screenshot_id)
        click.echo(format_delete_screenshot(response, ctx.obj["json_output"]))
    except ShortcutyAPIError as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.pass_context
def check_updates(ctx):
    """Check for available updates."""
    current_version = get_current_version()
    click.echo(f"Current version: {current_version}")
    click.echo("Checking for updates...")
    
    try:
        update_info = check_for_updates()
        if update_info:
            latest_version = update_info.get("version", "unknown")
            click.echo(f"\nUpdate available: {current_version} -> {latest_version}")
            click.echo(f"Run 'shortcuty cli-update' to install the update.")
            update_cache_timestamp()
        else:
            click.echo("You are already running the latest version!")
            update_cache_timestamp()
    except Exception as e:
        click.echo(f"Error checking for updates: {e}", err=True)
        ctx.exit(1)


@cli.command(name="cli-update")
@click.pass_context
def cli_update(ctx):
    """Update to the latest version."""
    current_version = get_current_version()
    click.echo(f"Current version: {current_version}")
    click.echo("Checking for updates...")
    
    try:
        update_info = check_for_updates()
        if update_info:
            latest_version = update_info.get("version", "unknown")
            click.echo(f"\nUpdating from {current_version} to {latest_version}...")
            
            if install_update():
                click.echo(f"Successfully updated to version {latest_version}!")
                click.echo("Please restart the CLI to use the new version.")
                update_cache_timestamp()
            else:
                click.echo("Update installation failed. Please update manually:", err=True)
                click.echo(f"  pip install --upgrade git+https://github.com/Shortcuty/Shortcuty-CLI.git", err=True)
                ctx.exit(1)
        else:
            click.echo("You are already running the latest version!")
            update_cache_timestamp()
    except Exception as e:
        click.echo(f"Error updating: {e}", err=True)
        ctx.exit(1)


def main():
    """Entry point for the CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()

