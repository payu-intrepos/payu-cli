"""Shared command runner — handles asyncio dispatch and error reporting."""

from __future__ import annotations

import asyncio
from typing import Awaitable, Callable

import httpx
import typer

from payu_cli.formatters import fmt_error


def _format_http_error(e: httpx.HTTPStatusError) -> str:
    """Build a useful message from an HTTPStatusError, including response body."""
    body = (e.response.text or "").strip()
    if len(body) > 800:
        body = body[:800] + "…"
    base = f"HTTP {e.response.status_code} {e.response.reason_phrase} — {e.request.method} {e.request.url}"
    return f"{base}\n\n{body}" if body else base


def run_async(coro_factory: Callable[[], Awaitable[dict]], formatter: Callable[[dict], None]) -> None:
    """Run an async API call and print its result.

    `coro_factory` is a zero-arg callable returning a coroutine (so the event
    loop owns awaitable creation). On any error, prints a friendly message via
    `fmt_error` and exits with code 1.
    """
    try:
        data = asyncio.run(coro_factory())
    except httpx.HTTPStatusError as e:
        fmt_error(_format_http_error(e))
        raise typer.Exit(1) from None
    except httpx.RequestError as e:
        fmt_error(f"Network error: {e}")
        raise typer.Exit(1) from None
    except (RuntimeError, ValueError) as e:
        fmt_error(str(e))
        raise typer.Exit(1) from None
    except KeyboardInterrupt:
        fmt_error("Interrupted")
        raise typer.Exit(130) from None

    formatter(data)
