"""Commands: payu refund ..."""

from __future__ import annotations

from typing import Optional

import typer

from payu_cli._runner import run_async
from payu_cli.api import PayUClient
from payu_cli.formatters import fmt_error, fmt_refunds, fmt_refunds_summary

app = typer.Typer(name="refund", help="Refund search & analytics", no_args_is_help=True)

VALID_STATUSES = ("requested", "success", "failure", "queued", "pending", "user_cancelled")


def _validate_status(status: str) -> None:
    if status and status not in VALID_STATUSES:
        fmt_error(f"Invalid status '{status}'. Valid: {', '.join(VALID_STATUSES)}")
        raise typer.Exit(1)


@app.command("search")
def search(
    date_from: str = typer.Option(..., "--from", help="Start date (YYYY-MM-DD)"),
    date_to: str = typer.Option(..., "--to", help="End date   (YYYY-MM-DD)"),
    status: str = typer.Option(
        "",
        "--status",
        "-s",
        help=f"Status filter ({', '.join(VALID_STATUSES)})",
    ),
    offset: int = typer.Option(0, "--offset", help="Page offset"),
    limit: int = typer.Option(10, "--limit", help="Page size"),
    profile: Optional[str] = typer.Option(None, "--profile"),
):
    """Search refunds by date range and status."""
    _validate_status(status)

    async def _run():
        async with PayUClient(profile) as client:
            return await client.search_refunds(
                date_from, date_to, page_offset=offset, page_size=limit, status=status,
            )

    run_async(_run, fmt_refunds)


@app.command("summary")
def summary(
    date_from: str = typer.Option(..., "--from", help="Start date (YYYY-MM-DD)"),
    date_to: str = typer.Option(..., "--to", help="End date   (YYYY-MM-DD)"),
    status: str = typer.Option("", "--status", "-s", help="Status filter"),
    profile: Optional[str] = typer.Option(None, "--profile"),
):
    """Get refund summary analytics."""
    _validate_status(status)

    async def _run():
        async with PayUClient(profile) as client:
            return await client.refunds_summary(date_from, date_to, status=status)

    run_async(_run, fmt_refunds_summary)
