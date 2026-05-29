"""Custom Typer Group that shows a cleaner usage line."""

from __future__ import annotations

import click
from typer.core import TyperGroup


class CleanGroup(TyperGroup):
    """Removes '[OPTIONS]' from the usage line since the only option is --help."""

    def format_usage(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        pieces = self.collect_usage_pieces(ctx)
        pieces = [p for p in pieces if p != "[OPTIONS]"]
        formatter.write_usage(ctx.command_path, " ".join(pieces))
