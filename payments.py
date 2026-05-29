"""
Commands: payu pay ...
"""

from __future__ import annotations

import asyncio
from typing import Optional

import typer

from payu_cli.api import PayUClient
from payu_cli.formatters import fmt_payment_link, fmt_invoice_details, fmt_error

app = typer.Typer(name="pay", help="Payment links & invoices")


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

    try:
        data = asyncio.run(_run())
        fmt_payment_link(data)
    except Exception as e:
        fmt_error(str(e))
        raise typer.Exit(1)


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

    try:
        data = asyncio.run(_run())
        fmt_invoice_details(data, invoice_id)
    except Exception as e:
        fmt_error(str(e))
        raise typer.Exit(1)
