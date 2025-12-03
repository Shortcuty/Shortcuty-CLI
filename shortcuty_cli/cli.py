"""Command-line interface for Shortcuty Creator API."""

import click
from shortcuty_cli.api_client import ShortcutyAPIClient, ShortcutyAPIError
from shortcuty_cli.config import get_api_key
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
@click.pass_context
def cli(ctx, api_key, json_output):
    """Shortcuty Creator API CLI - Manage shortcuts programmatically."""
    ctx.ensure_object(dict)
    api_key = get_api_key(api_key)
    ctx.obj["api_key"] = api_key
    ctx.obj["json_output"] = json_output
    ctx.obj["client"] = ShortcutyAPIClient(api_key=api_key)


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
@click.option("--submit", is_flag=True, help="Submit for review immediately")
@click.pass_context
def create(ctx, sharing_url, description, category, requires_ios26_ai, updater_type, submit):
    """Create a new shortcut."""
    if not ctx.obj["api_key"]:
        click.echo("Error: API key required. Use --api-key or set SHORTCUTY_API_KEY.", err=True)
        ctx.exit(1)
    
    try:
        client = ctx.obj["client"]
        response = client.create_shortcut(
            sharing_url=sharing_url,
            description=description,
            category=category,
            requires_ios26_ai=requires_ios26_ai if requires_ios26_ai else None,
            updater_type=updater_type,
            submit=submit if submit else None,
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
def list(ctx, page, per_page):
    """List your shortcuts."""
    if not ctx.obj["api_key"]:
        click.echo("Error: API key required. Use --api-key or set SHORTCUTY_API_KEY.", err=True)
        ctx.exit(1)
    
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
def get(ctx, uuid):
    """Get shortcut details by UUID."""
    if not ctx.obj["api_key"]:
        click.echo("Error: API key required. Use --api-key or set SHORTCUTY_API_KEY.", err=True)
        ctx.exit(1)
    
    try:
        client = ctx.obj["client"]
        response = client.get_shortcut(uuid)
        click.echo(format_shortcut_details(response, ctx.obj["json_output"]))
    except ShortcutyAPIError as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.argument("identifier")
@click.pass_context
def history(ctx, identifier):
    """Get version history for a shortcut."""
    if not ctx.obj["api_key"]:
        click.echo("Error: API key required. Use --api-key or set SHORTCUTY_API_KEY.", err=True)
        ctx.exit(1)
    
    try:
        client = ctx.obj["client"]
        response = client.get_shortcut_history(identifier)
        click.echo(format_history(response, ctx.obj["json_output"]))
    except ShortcutyAPIError as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.argument("uuid")
@click.pass_context
def submit(ctx, uuid):
    """Submit shortcut for review."""
    if not ctx.obj["api_key"]:
        click.echo("Error: API key required. Use --api-key or set SHORTCUTY_API_KEY.", err=True)
        ctx.exit(1)
    
    try:
        client = ctx.obj["client"]
        response = client.submit_shortcut(uuid)
        click.echo(format_message(response, ctx.obj["json_output"]))
    except ShortcutyAPIError as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)


@cli.command()
@click.argument("uuid")
@click.option("--name", help="Shortcut name")
@click.option("--description", help="Shortcut description")
@click.option("--sharing-url", help="iCloud sharing URL")
@click.option("--category", help="Category name")
@click.option("--requires-ios26-ai", is_flag=True, help="Requires iOS 26 AI features")
@click.option(
    "--updater-type",
    type=click.Choice(["shortcuty", "third_party", "none"], case_sensitive=False),
    help="Updater type",
)
@click.option("--new-version", help="New version string (e.g., '2.0')")
@click.option("--changelog", help="Changelog text")
@click.pass_context
def update(
    ctx,
    uuid,
    name,
    description,
    sharing_url,
    category,
    requires_ios26_ai,
    updater_type,
    new_version,
    changelog,
):
    """Update an existing shortcut."""
    if not ctx.obj["api_key"]:
        click.echo("Error: API key required. Use --api-key or set SHORTCUTY_API_KEY.", err=True)
        ctx.exit(1)
    
    if not any([name, description, sharing_url, category, requires_ios26_ai, updater_type, new_version, changelog]):
        click.echo("Error: At least one update field must be provided.", err=True)
        ctx.exit(1)
    
    try:
        client = ctx.obj["client"]
        response = client.update_shortcut(
            uuid=uuid,
            name=name,
            description=description,
            sharing_url=sharing_url,
            category=category,
            requires_ios26_ai=requires_ios26_ai if requires_ios26_ai else None,
            updater_type=updater_type,
            new_version=new_version,
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
def upload_screenshot(ctx, uuid, file):
    """Upload a screenshot for a shortcut."""
    if not ctx.obj["api_key"]:
        click.echo("Error: API key required. Use --api-key or set SHORTCUTY_API_KEY.", err=True)
        ctx.exit(1)
    
    try:
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
def delete_screenshot(ctx, uuid, screenshot_id):
    """Delete a screenshot for a shortcut."""
    if not ctx.obj["api_key"]:
        click.echo("Error: API key required. Use --api-key or set SHORTCUTY_API_KEY.", err=True)
        ctx.exit(1)
    
    try:
        client = ctx.obj["client"]
        response = client.delete_screenshot(uuid, screenshot_id)
        click.echo(format_delete_screenshot(response, ctx.obj["json_output"]))
    except ShortcutyAPIError as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)


def main():
    """Entry point for the CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()

