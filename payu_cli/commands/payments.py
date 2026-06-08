"""Commands: payu pay ..."""

from __future__ import annotations

from typing import Optional

import typer

from payu_cli._runner import run_async
from payu_cli.api import PayUClient
from payu_cli.formatters import fmt_error, fmt_invoice_details, fmt_json, fmt_payment_link

app = typer.Typer(name="pay", help="Payment links & invoices", no_args_is_help=True)


@app.command("create-link")
def create_link(
    amount: float = typer.Option(..., "--amount", "-a", help="Payment amount"),
    description: str = typer.Option(..., "--desc", "-d", help="Payment description"),
    name: str = typer.Option("", "--name", "-n", help="Customer name"),
    phone: str = typer.Option("", "--phone", "-p", help="Customer phone (+91...)"),
    email: str = typer.Option("", "--email", "-e", help="Customer email"),
    profile: Optional[str] = typer.Option(None, "--profile", help="Credential profile"),
):
    """Create a payment link and optionally send via SMS/email."""

    async def _run():
        async with PayUClient(profile) as client:
            return await client.create_payment_link(
                amount=amount,
                description=description,
                name=name,
                phone=phone,
                email=email,
            )

    run_async(_run, fmt_payment_link)


@app.command("invoice")
def invoice(
    invoice_id: str = typer.Argument(help="Invoice / payment-link ID"),
    date_from: str = typer.Option("", "--from", help="Start date (YYYY-MM-DD)"),
    date_to: str = typer.Option("", "--to", help="End date (YYYY-MM-DD)"),
    offset: int = typer.Option(0, "--offset", help="Page offset"),
    limit: int = typer.Option(10, "--limit", help="Page size"),
    profile: Optional[str] = typer.Option(None, "--profile", help="Credential profile"),
):
    """Get transactions for a payment-link / invoice."""

    async def _run():
        async with PayUClient(profile) as client:
            return await client.get_invoice_details(
                invoice_id,
                date_from=date_from,
                date_to=date_to,
                page_offset=offset,
                page_size=limit,
            )

    run_async(_run, lambda data: fmt_invoice_details(data, invoice_id))


@app.command("send")
def send(
    invoice_number: str = typer.Argument(help="Invoice number of the payment link"),
    via_email: bool = typer.Option(False, "--email", help="Send via email"),
    via_sms: bool = typer.Option(False, "--sms", help="Send via SMS"),
    profile: Optional[str] = typer.Option(None, "--profile"),
):
    """Send/resend a payment link via email or SMS."""
    if not via_email and not via_sms:
        fmt_error("Specify at least one of --email or --sms")
        raise typer.Exit(1)

    async def _run():
        async with PayUClient(profile) as client:
            return await client.send_payment_link(
                invoice_number, via_email=via_email, via_sms=via_sms
            )

    run_async(_run, fmt_json)


@app.command("status")
def status(
    invoice_number: str = typer.Argument(help="Invoice number to look up"),
    profile: Optional[str] = typer.Option(None, "--profile"),
):
    """Get payment link details by invoice number."""

    async def _run():
        async with PayUClient(profile) as client:
            return await client.get_payment_link(invoice_number)

    run_async(_run, fmt_json)


@app.command("list")
def list_links(
    date_from: str = typer.Option("", "--from", help="Start date (YYYY-MM-DD), default last 30 days"),
    date_to: str = typer.Option("", "--to", help="End date (YYYY-MM-DD), default today"),
    offset: int = typer.Option(0, "--offset", help="Page offset"),
    limit: int = typer.Option(20, "--limit", help="Page size"),
    profile: Optional[str] = typer.Option(None, "--profile"),
):
    """List all payment links."""

    async def _run():
        async with PayUClient(profile) as client:
            return await client.list_payment_links(
                date_from=date_from,
                date_to=date_to,
                page_offset=offset,
                page_size=limit,
            )

    run_async(_run, fmt_json)


@app.command("update")
def update(
    invoice_number: str = typer.Argument(help="Invoice number to update"),
    description: str = typer.Option("", "--desc", "-d", help="New description"),
    expiry: str = typer.Option("", "--expiry", help="New expiry (YYYY-MM-DD HH:MM:SS)"),
    active: str = typer.Option("", "--active", help="Set active status (true/false)"),
    profile: Optional[str] = typer.Option(None, "--profile"),
):
    """Update a payment link's description, expiry, or status."""
    if not description and not expiry and not active:
        fmt_error("Specify at least one of --desc, --expiry, or --active")
        raise typer.Exit(1)

    async def _run():
        async with PayUClient(profile) as client:
            return await client.update_payment_link(
                invoice_number,
                description=description,
                expiry_date=expiry,
                is_active=active,
            )

    run_async(_run, fmt_json)
