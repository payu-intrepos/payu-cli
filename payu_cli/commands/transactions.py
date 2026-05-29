"""
Commands: payu txn ...
"""

from __future__ import annotations

import asyncio
from typing import Optional

import typer

from payu_cli.api import PayUClient
from payu_cli.formatters import (
    fmt_transaction,
    fmt_transactions_list,
    fmt_transactions_summary,
    fmt_error,
)

app = typer.Typer(name="txn", help="Transactions — get, list, summary", no_args_is_help=True)


def _split(value: str) -> list[str] | None:
    """Split comma-separated string into list, or None if empty."""
    return [v.strip() for v in value.split(",") if v.strip()] or None


# ------------------------------------------------------------------
# payu txn get <id>
# ------------------------------------------------------------------

@app.command("get")
def get(
    payu_id: str = typer.Argument(help="PayU transaction ID"),
    profile: Optional[str] = typer.Option(None, "--profile"),
):
    """Fetch full details for a single transaction."""

    async def _run():
        async with PayUClient(profile) as client:
            return await client.get_transaction(payu_id)

    try:
        data = asyncio.run(_run())
        fmt_transaction(data)
    except Exception as e:
        fmt_error(str(e))
        raise typer.Exit(1)


# ------------------------------------------------------------------
# payu txn list --from ... --to ...
# ------------------------------------------------------------------

@app.command("list")
def list_txns(
    date_from: str = typer.Option(..., "--from", help="Start (YYYY-MM-DD HH:MM:SS)"),
    date_to: str = typer.Option(..., "--to", help="End   (YYYY-MM-DD HH:MM:SS)"),
    offset: int = typer.Option(0, "--offset", help="Page offset"),
    limit: int = typer.Option(20, "--limit", help="Records per page"),
    status: str = typer.Option("", "--status", "-s", help="Status filter (comma-sep: captured,failed,...)"),
    mode: str = typer.Option("", "--mode", "-m", help="Payment mode (comma-sep: UPI,CC,DC,NB,EMI,...)"),
    source: str = typer.Option("", "--source", help="Payment source (comma-sep: pg,paymentLink,...)"),
    pa: str = typer.Option("", "--pa", help="Aggregator (comma-sep: PayU,AxisCyber,RazorPay)"),
    currency: str = typer.Option("", "--currency", help="Currency (comma-sep: USD,AED,...)"),
    filters: str = typer.Option("", "--filters", help="Extra filters (comma-sep: ivr,mobile,tpv,...)"),
    min_amount: Optional[float] = typer.Option(None, "--min-amount", help="Min amount"),
    max_amount: Optional[float] = typer.Option(None, "--max-amount", help="Max amount"),
    profile: Optional[str] = typer.Option(None, "--profile"),
):
    """List transactions with filters."""

    # Validate paired amount params
    if (min_amount is None) != (max_amount is None):
        fmt_error("--min-amount and --max-amount must be provided together (PayU API requirement)")
        raise typer.Exit(1)

    async def _run():
        async with PayUClient(profile) as client:
            return await client.list_transactions(
                date_from,
                date_to,
                page_offset=offset,
                page_limit=limit,
                status=_split(status),
                mode=_split(mode),
                payment_source=_split(source),
                pa=_split(pa),
                currency=_split(currency),
                more_filters=_split(filters),
                min_amount=min_amount,
                max_amount=max_amount,
            )

    try:
        data = asyncio.run(_run())
        fmt_transactions_list(data)
    except Exception as e:
        fmt_error(str(e))
        raise typer.Exit(1)


# ------------------------------------------------------------------
# payu txn summary --from ... --to ...
# ------------------------------------------------------------------

@app.command("summary")
def summary(
    date_from: str = typer.Option(..., "--from", help="Start (YYYY-MM-DD HH:MM:SS)"),
    date_to: str = typer.Option(..., "--to", help="End   (YYYY-MM-DD HH:MM:SS)"),
    status: str = typer.Option("", "--status", "-s", help="Status filter (comma-sep)"),
    mode: str = typer.Option("", "--mode", "-m", help="Payment mode (comma-sep)"),
    source: str = typer.Option("", "--source", help="Payment source (comma-sep)"),
    currency: str = typer.Option("", "--currency", help="Currency filter (comma-sep)"),
    pa: str = typer.Option("", "--pa", help="Aggregator filter (comma-sep)"),
    filters: str = typer.Option("", "--filters", help="Extra filters (comma-sep)"),
    min_amount: Optional[float] = typer.Option(None, "--min-amount"),
    max_amount: Optional[float] = typer.Option(None, "--max-amount"),
    profile: Optional[str] = typer.Option(None, "--profile"),
):
    """Get aggregated transaction summary with filters."""

    if (min_amount is None) != (max_amount is None):
        fmt_error("--min-amount and --max-amount must be provided together")
        raise typer.Exit(1)

    async def _run():
        async with PayUClient(profile) as client:
            return await client.transactions_summary(
                date_from,
                date_to,
                status=_split(status),
                mode=_split(mode),
                payment_source=_split(source),
                currency=_split(currency),
                pa=_split(pa),
                more_filters=_split(filters),
                min_amount=min_amount,
                max_amount=max_amount,
            )

    try:
        data = asyncio.run(_run())
        fmt_transactions_summary(data)
    except Exception as e:
        fmt_error(str(e))
        raise typer.Exit(1)
