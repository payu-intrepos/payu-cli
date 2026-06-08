"""
payu — CLI for PayU dashboard APIs.

Usage:
    payu config set          Configure credentials
    payu account list        List saved credential profiles
    payu account switch      Switch active profile
    payu pay create-link     Create a payment link
    payu pay send            Send a payment link via email/SMS
    payu pay status          Get payment link details
    payu pay list            List all payment links
    payu pay update          Update a payment link
    payu pay invoice         Get invoice / payment-link transactions
    payu txn get             Get single transaction details
    payu txn list            List transactions with filters
    payu txn summary         Aggregated transaction analytics
    payu refund search       Search refunds
    payu refund summary      Refund analytics
    payu settlement get      Settlement details
    payu report create       Generate a CSV report
    payu report get          Download a report
"""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from payu_cli import __version__
from payu_cli.cli_group import CleanGroup
from payu_cli.commands.payments import app as pay_app
from payu_cli.commands.refunds import app as refund_app
from payu_cli.commands.reports import app as report_app
from payu_cli.commands.settlements import app as settlement_app
from payu_cli.commands.transactions import app as txn_app
from payu_cli.config import delete_profile, list_profiles, load_profile, save_profile
from payu_cli.formatters import fmt_error

console = Console()


# ---------------------------------------------------------------------------
# Root app
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="payu",
    help="CLI for PayU payment operations",
    no_args_is_help=True,
    rich_markup_mode="rich",
    cls=CleanGroup,
)

# Register sub-command groups.
for sub_app in (pay_app, txn_app, refund_app, settlement_app, report_app):
    app.add_typer(sub_app, cls=CleanGroup)


# ---------------------------------------------------------------------------
# payu version
# ---------------------------------------------------------------------------

@app.command("version")
def version():
    """Print CLI version."""
    console.print(f"payu-cli [bold green]{__version__}[/bold green]")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _show_profile(profile: Optional[str]) -> None:
    """Print the resolved profile, masking the secret."""
    creds = load_profile(profile)
    table = Table(title=f"Profile: {creds['profile']}", show_header=False, border_style="blue")
    table.add_column("Key", style="bold")
    table.add_column("Value")
    table.add_row("client_id", creds["client_id"] or "[dim]not set[/dim]")
    secret = creds["client_secret"]
    table.add_row(
        "client_secret",
        ("••••" + secret[-4:]) if secret else "[dim]not set[/dim]",
    )
    table.add_row("merchant_id", creds["merchant_id"] or "[dim]not set[/dim]")
    table.add_row("env", creds["env"])
    console.print(table)


# ---------------------------------------------------------------------------
# payu config ...
# ---------------------------------------------------------------------------

config_app = typer.Typer(
    name="config", help="Manage credential profiles", no_args_is_help=True, cls=CleanGroup,
)
app.add_typer(config_app)


@config_app.command("set")
def config_set(
    profile: str = typer.Option("default", "--profile", "-p", help="Profile name"),
    client_id: str = typer.Option(..., "--client-id", prompt=True, help="PayU Client ID"),
    client_secret: str = typer.Option(
        ..., "--client-secret", prompt=True, hide_input=True, help="PayU Client Secret",
    ),
    merchant_id: str = typer.Option(..., "--merchant-id", prompt=True, help="Merchant ID"),
    env: str = typer.Option("production", "--env", help="Environment (production / test)"),
):
    """Save a credential profile (secrets go to OS keyring when available)."""
    save_profile(
        profile,
        client_id=client_id,
        client_secret=client_secret,
        merchant_id=merchant_id,
        env=env,
    )


@config_app.command("show")
def config_show(profile: Optional[str] = typer.Option(None, "--profile", "-p")):
    """Display the active profile (secrets are masked)."""
    _show_profile(profile)


@config_app.command("list")
def config_list():
    """List all saved profiles."""
    profiles = list_profiles()
    if not profiles:
        console.print("[yellow]No profiles configured. Run `payu config set` to create one.[/yellow]")
        return
    for p in profiles:
        console.print(f"  • {p}")


@config_app.command("delete")
def config_delete(profile: str = typer.Argument(help="Profile name to delete")):
    """Delete a saved profile."""
    delete_profile(profile)


# ---------------------------------------------------------------------------
# payu account ...
# ---------------------------------------------------------------------------

account_app = typer.Typer(
    name="account", help="Manage merchant accounts (profiles)", no_args_is_help=True, cls=CleanGroup,
)
app.add_typer(account_app)


@account_app.command("list")
def account_list():
    """List all configured merchant accounts."""
    profiles = list_profiles()
    if not profiles:
        console.print("[yellow]No accounts configured. Run `payu account add` to create one.[/yellow]")
        return
    active = load_profile()["profile"]
    for p in profiles:
        marker = " [bold green]← active[/bold green]" if p == active else ""
        console.print(f"  • {p}{marker}")


@account_app.command("show")
def account_show(profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to show")):
    """Show the current active merchant account."""
    _show_profile(profile)


@account_app.command("add")
def account_add(
    profile: str = typer.Option("default", "--profile", "-p", help="Profile name"),
    client_id: str = typer.Option(..., "--client-id", prompt=True, help="PayU Client ID"),
    client_secret: str = typer.Option(
        ..., "--client-secret", prompt=True, hide_input=True, help="PayU Client Secret",
    ),
    merchant_id: str = typer.Option(..., "--merchant-id", prompt=True, help="Merchant ID"),
    env: str = typer.Option("production", "--env", help="Environment (production / test)"),
):
    """Add a new merchant account."""
    save_profile(
        profile,
        client_id=client_id,
        client_secret=client_secret,
        merchant_id=merchant_id,
        env=env,
    )


@account_app.command("switch")
def account_switch(profile: str = typer.Argument(help="Profile name to switch to")):
    """Switch the active account by setting PAYU_PROFILE."""
    profiles = list_profiles()
    if profile not in profiles:
        fmt_error(
            f"Profile '{profile}' not found. "
            f"Available: {', '.join(profiles) if profiles else '(none)'}"
        )
        raise typer.Exit(1)
    console.print(f"[green]✓[/green] To switch, run: [bold]export PAYU_PROFILE={profile}[/bold]")
    console.print(f"  Or pass [bold]--profile {profile}[/bold] to any command.")


@account_app.command("remove")
def account_remove(profile: str = typer.Argument(help="Profile name to remove")):
    """Remove a merchant account."""
    delete_profile(profile)


if __name__ == "__main__":
    app()
