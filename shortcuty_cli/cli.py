"""Command-line interface for Shortcuty Creator API."""

import functools
import math
import click
from shortcuty_cli.api_client import ShortcutyAPIClient, ShortcutyAPIError, validate_image_file
from shortcuty_cli.config import get_api_key
from shortcuty_cli.signing import sign_shortcut
from shortcuty_cli import __version__
from shortcuty_cli.formatters import format_json
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


def finite_timeout(ctx, param, value):
    if not math.isfinite(value):
        raise click.BadParameter("Timeout must be finite", ctx=ctx, param=param)
    return value


def require_api_key(f):
    """Decorator to require API key for a command."""
    @functools.wraps(f)
    def wrapper(ctx, *args, **kwargs):
        if not ctx.obj["api_key"]:
            click.echo("Error: API key required. Use --api-key or set SHORTCUTY_API_KEY environment variable.", err=True)
            ctx.exit(1)
        return f(ctx, *args, **kwargs)
    return wrapper


@click.group()
@click.version_option(version=__version__)
@click.option("--timeout", type=click.FloatRange(min=0, min_open=True), callback=finite_timeout, default=60, show_default=True, help="API read timeout in seconds (connect timeout: 10s)")
@click.option("--body-format", type=click.Choice(["json", "form"]), default="json", show_default=True, help="Create/update request encoding")
@click.option(
    "--api-key",
    envvar="SHORTCUTY_API_KEY",
    help="API key for authentication (can also use SHORTCUTY_API_KEY env var)",
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
def cli(ctx, api_key, json_output, no_check_updates, timeout, body_format):
    """Shortcuty Creator API CLI - Manage shortcuts programmatically."""
    ctx.ensure_object(dict)
    api_key = get_api_key(api_key)
    ctx.obj["api_key"] = api_key
    ctx.obj["json_output"] = json_output
    ctx.obj["client"] = ShortcutyAPIClient(api_key=api_key, timeout=timeout, body_format=body_format)
    ctx.obj["no_check_updates"] = no_check_updates
    ctx.call_on_close(ctx.obj["client"].close)
    


@cli.result_callback()
@click.pass_context
def automatic_update_check(ctx, result, **kwargs):
    """Check after successful commands; keep help, signing and JSON offline/clean."""
    if (not ctx.obj["no_check_updates"] and not ctx.obj["json_output"]
            and ctx.invoked_subcommand not in ("sign", "check-updates", "cli-update")
            and should_check_updates()):
        try:
            update_info = check_for_updates()
            if update_info:
                show_update_notification(update_info)
            update_cache_timestamp()
        except Exception:
            pass


@cli.command()
@click.pass_context
def categories(ctx):
    """List all available categories (public endpoint)."""
    try:
        client = ShortcutyAPIClient(timeout=ctx.obj["client"].timeout)
        try:
            categories_list = client.get_categories()
        finally:
            client.close()
        click.echo(format_categories(categories_list, ctx.obj["json_output"]))
    except ShortcutyAPIError as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.option("--sharing-url", required=True, help="iCloud sharing URL")
@click.option("--description", help="Shortcut description")
@click.option("--category", help="Category name")
@click.option("--requires-ios26-ai/--no-requires-ios26-ai", default=None, help="Whether iOS 26 AI features are required")
@click.option("--visibility", type=click.Choice(["public", "private"]), help="Shortcut visibility")
@click.option(
    "--updater-type",
    type=click.Choice(["shortcuty", "third_party", "none"], case_sensitive=False),
    help="Updater type",
)
@click.option("--auto-submit", is_flag=True, help="Submit for review immediately")
@click.pass_context
@require_api_key
def create(ctx, sharing_url, description, category, requires_ios26_ai, updater_type, auto_submit, visibility):
    """Create a new shortcut."""
    try:
        client = ctx.obj["client"]
        response = client.create_shortcut(
            sharing_url=sharing_url,
            description=description,
            category=category,
            requires_ios26_ai=requires_ios26_ai,
            updater_type=updater_type,
            auto_submit=auto_submit if auto_submit else None,
            visibility=visibility,
        )
        shortcut = response.get("shortcut", {})
        if not ctx.obj["json_output"]:
            click.echo(format_message(response))
        click.echo(format_shortcut(shortcut, ctx.obj["json_output"]))
    except ShortcutyAPIError as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.option("--page", type=click.IntRange(min=1), default=1, help="Page number")
@click.option("--per-page", type=click.IntRange(min=1), default=20, help="Items per page")
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
@click.option("--requires-ios26-ai/--no-requires-ios26-ai", default=None, help="Whether iOS 26 AI features are required")
@click.option("--visibility", type=click.Choice(["public", "private"]), help="Shortcut visibility")
@click.option(
    "--updater-type",
    type=click.Choice(["shortcuty", "third_party", "none"], case_sensitive=False),
    help="Updater type",
)
@click.option("--version", help="Version string (e.g., '2.0')")
@click.option("--changelog", help="Changelog text")
@click.option("--clear-description", is_flag=True, help="Set description to JSON null")
@click.option("--clear-category", is_flag=True, help="Set category to JSON null")
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
    visibility,
    clear_description,
    clear_category,
):
    """Update a shortcut. Send all changes to keep when replacing a pending proposal."""
    if (clear_description and description is not None) or (clear_category and category is not None):
        raise click.UsageError("Use either a field value or its --clear option")
    if not (any(value is not None for value in
                [description, sharing_url, category, requires_ios26_ai, updater_type, version, changelog, visibility])
            or clear_description or clear_category):
        click.echo("Error: At least one update field must be provided.", err=True)
        ctx.exit(1)
    
    try:
        client = ctx.obj["client"]
        response = client.update_shortcut(
            uuid=uuid,
            description=description,
            sharing_url=sharing_url,
            category=category,
            requires_ios26_ai=requires_ios26_ai,
            updater_type=updater_type,
            version=version,
            changelog=changelog,
            visibility=visibility,
            clear_description=clear_description,
            clear_category=clear_category,
        )
        click.echo(format_message(response, ctx.obj["json_output"]))
    except ShortcutyAPIError as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.argument("uuid")
@click.argument("file", type=click.Path(exists=True, readable=True, dir_okay=False))
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
@click.argument("screenshot_id", type=click.IntRange(min=1))
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
@click.argument("file", type=click.Path(exists=True, readable=True, dir_okay=False))
@click.option("--output", "-o", type=click.Path(dir_okay=False), help="Output file path (default: sanitized server filename in current directory)")
@click.option("--force", is_flag=True, help="Allow replacing an existing output, including the input")
@click.option("--timeout", type=click.FloatRange(min=0, min_open=True), callback=finite_timeout, default=300, show_default=True, help="Signing read timeout in seconds, including queue wait")
@click.pass_context
def sign(ctx, file, output, force, timeout):
    """Upload an unsigned .shortcut and save its signed file. No API key required."""
    click.echo("Signing shortcut; waiting for the server...", err=True)
    try:
        result = sign_shortcut(file, output=output, force=force, timeout=timeout)
        click.echo(format_json(result) if ctx.obj["json_output"] else "Signed shortcut saved to " + result["output"])
    except ShortcutyAPIError as error:
        raise click.ClickException(str(error)) from None


@cli.command()
@click.pass_context
def check_updates(ctx):
    """Check for available updates."""
    try:
        update_info = check_for_updates()
        update_cache_timestamp()
        result = {"current_version": get_current_version(), "update_available": update_info is not None}
        if update_info:
            result.update(update_info)
        if ctx.obj["json_output"]:
            click.echo(format_json(result))
        elif update_info:
            click.echo(f"Update available: {result['current_version']} -> {result['version']}")
            click.echo("Run 'shortcuty cli-update' to install it.")
        else:
            click.echo(f"Already running the latest version ({result['current_version']}).")
    except ShortcutyAPIError as error:
        raise click.ClickException(str(error)) from None


@cli.command(name="cli-update")
@click.pass_context
def cli_update(ctx):
    """Install the current GitHub main in this Python environment."""
    click.echo("Installing CLI from GitHub...", err=True)
    if not install_update():
        raise click.ClickException("Installation failed. Run python -m pip install --upgrade "
                                   "git+https://github.com/Shortcuty/Shortcuty-CLI.git")
    update_cache_timestamp()
    result = {"installed": True, "source": "https://github.com/Shortcuty/Shortcuty-CLI"}
    click.echo(format_json(result) if ctx.obj["json_output"] else "CLI updated. Restart the CLI to use it.")


def main():
    """Entry point for the CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()

