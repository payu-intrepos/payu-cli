"""
Commands: payu report ...
"""

from __future__ import annotations

import asyncio
from typing import Optional

import typer

from payu_cli.api import PayUClient
from payu_cli.formatters import fmt_json, fmt_error

VALID_SERVICES = ["transactions", "settlements", "refunds", "payouts"]

app = typer.Typer(name="report", help="Generate & download CSV reports", no_args_is_help=True)


@app.command("create")
def create(
    service: str = typer.Argument(
        help=f"Report type ({', '.join(VALID_SERVICES)})",
    ),
    date_from: str = typer.Option(..., "--from", help="Start (YYYY-MM-DD HH:MM:SS)"),
    date_to: str = typer.Option(..., "--to", help="End   (YYYY-MM-DD HH:MM:SS)"),
    profile: Optional[str] = typer.Option(None, "--profile"),
):
    """Create a CSV report for transactions, settlements, refunds, or payouts."""
    if service not in VALID_SERVICES:
        fmt_error(f"Invalid service '{service}'. Valid: {', '.join(VALID_SERVICES)}")
        raise typer.Exit(1)

    async def _run():
        async with PayUClient(profile) as client:
            return await client.create_report(service, date_from, date_to)

    try:
        data = asyncio.run(_run())
        fmt_json(data)
    except Exception as e:
        fmt_error(str(e))
        raise typer.Exit(1)


@app.command("get")
def get(
    report_id: str = typer.Argument(help="Report ID returned by 'report create'"),
    profile: Optional[str] = typer.Option(None, "--profile"),
):
    """Fetch report status and download URL."""

    async def _run():
        async with PayUClient(profile) as client:
            return await client.get_report(report_id)

    try:
        data = asyncio.run(_run())
        fmt_json(data)
    except Exception as e:
        fmt_error(str(e))
        raise typer.Exit(1)
