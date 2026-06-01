"""Commands: payu settlement ..."""

from __future__ import annotations

from typing import Optional

import typer

from payu_cli._runner import run_async
from payu_cli.api import PayUClient
from payu_cli.formatters import fmt_settlement

app = typer.Typer(name="settlement", help="Settlement details & tracking", no_args_is_help=True)


@app.command("get")
def get(
    settlement_id: str = typer.Argument(help="Settlement ID"),
    utr: str = typer.Option("", "--utr", help="UTR reference"),
    status: str = typer.Option("inprogress", "--status", "-s", help="Settlement status"),
    tid: str = typer.Option("", "--tid", help="Transaction ID"),
    profile: Optional[str] = typer.Option(None, "--profile"),
):
    """Fetch settlement details by ID, UTR, or transaction."""

    async def _run():
        async with PayUClient(profile) as client:
            return await client.get_settlement(settlement_id, utr=utr, status=status, tid=tid)

    run_async(_run, fmt_settlement)
