"""
Rich table formatters for every command output.

Each function takes a raw API dict and prints a styled table to stdout.
"""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


def _safe(d: dict, *keys: str, default: str = "—") -> str:
    """Nested safe-get."""
    cur: Any = d
    for k in keys:
        if isinstance(cur, dict):
            cur = cur.get(k, None)
        else:
            return default
    return str(cur) if cur is not None else default


def _as_float(value: Any) -> float:
    """Coerce API-supplied numeric (sometimes a string) into a float; 0.0 on failure."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


# ------------------------------------------------------------------
# Payment link
# ------------------------------------------------------------------


def fmt_payment_link(data: dict) -> None:
    result = data.get("result", {})
    if not result:
        console.print("[red]✗ Failed to create payment link[/red]")
        console.print(data.get("message", "Unknown error"))
        return

    table = Table(title="Payment Link Created", show_header=False, border_style="green")
    table.add_column("Field", style="bold")
    table.add_column("Value")

    table.add_row("Link", result.get("paymentLink", "—"))
    table.add_row("Invoice #", result.get("invoiceNumber", "—"))
    table.add_row("Description", result.get("description", "—"))
    table.add_row("Amount", str(result.get("subAmount", result.get("amount", "—"))))
    table.add_row("Status", result.get("status", "—"))

    console.print(table)


# ------------------------------------------------------------------
# Invoice details
# ------------------------------------------------------------------


def fmt_invoice_details(data: dict, invoice_id: str) -> None:
    result = data.get("result", {})
    rows = result.get("data", [])

    if not rows:
        console.print(f"[yellow]No transactions found for invoice {invoice_id}[/yellow]")
        return

    table = Table(title=f"Invoice {invoice_id} — Transactions")
    table.add_column("Txn ID", style="cyan")
    table.add_column("Date")
    table.add_column("Amount", justify="right", style="green")
    table.add_column("Status")
    table.add_column("Mode")
    table.add_column("Ref ID")

    for txn in rows[:20]:
        table.add_row(
            _safe(txn, "transactionId"),
            _safe(txn, "createdOn"),
            f"₹{_as_float(txn.get('settledAmount', 0)):,.2f}",
            _safe(txn, "status"),
            _safe(txn, "mode"),
            _safe(txn, "merchantReferenceId"),
        )

    total = result.get("rows", len(rows))
    console.print(table)
    if total > 20:
        console.print(f"  [dim]Showing 20 of {total} transactions[/dim]")
    console.print(
        f"  [dim]→ https://payu.in/business/payment-links/{invoice_id}[/dim]"
    )


# ------------------------------------------------------------------
# Single transaction
# ------------------------------------------------------------------


def fmt_transaction(data: dict) -> None:
    r = data.get("result", {})
    if not r:
        console.print(f"[red]✗ {data.get('message', 'Transaction not found')}[/red]")
        return

    pd = r.get("paymentDetails", {})
    cust = r.get("customer", {})

    table = Table(title="Transaction Details", show_header=False, border_style="cyan")
    table.add_column("Field", style="bold", min_width=22)
    table.add_column("Value")

    table.add_row("Payment ID", _safe(r, "paymentId"))
    table.add_row("Merchant Txn ID", _safe(r, "merchantTransactionId"))
    table.add_row("Status", _safe(r, "status"))
    table.add_row("Amount", _safe(r, "amount"))
    table.add_row("Date/Time", _safe(r, "transactionDateTime"))
    table.add_row("Mode", _safe(pd, "mode"))
    table.add_row("Bank Ref #", _safe(pd, "bankRefNo"))
    table.add_row("Source", _safe(r, "transactionSource"))
    table.add_row("Product Info", _safe(r, "productInfo"))
    table.add_row("Customer", _safe(cust, "name"))
    table.add_row("Refundable", _safe(r, "amountLeftForRefund"))
    table.add_row("PA", _safe(r, "pa_name"))

    console.print(table)


# ------------------------------------------------------------------
# Transactions list
# ------------------------------------------------------------------


def fmt_transactions_list(data: dict) -> None:
    result = data.get("result", data)
    # The API may nest data differently; adapt to common shapes
    rows = []
    if isinstance(result, dict):
        rows = result.get("data", result.get("transactions", []))
    elif isinstance(result, list):
        rows = result

    if not rows:
        console.print("[yellow]No transactions found for the given filters.[/yellow]")
        return

    table = Table(title="Transactions")
    table.add_column("#", style="dim")
    table.add_column("PayU ID", style="cyan")
    table.add_column("Merchant Txn ID")
    table.add_column("Amount", justify="right", style="green")
    table.add_column("Status")
    table.add_column("Mode")
    table.add_column("Date")

    for i, txn in enumerate(rows, 1):
        table.add_row(
            str(i),
            _safe(txn, "payuId", default=_safe(txn, "transactionId")),
            _safe(txn, "merchantTransactionId", default=_safe(txn, "merchantReferenceId")),
            _safe(txn, "amount", default=_safe(txn, "transactionAmount")),
            _safe(txn, "status"),
            _safe(txn, "mode"),
            _safe(txn, "createdOn", default=_safe(txn, "transactionDate")),
        )

    console.print(table)

    total = result.get("totalRows", result.get("rows", len(rows))) if isinstance(result, dict) else len(rows)
    if isinstance(total, (int, float)) and total > len(rows):
        console.print(f"  [dim]Showing {len(rows)} of {total} — use --offset / --limit to paginate[/dim]")


# ------------------------------------------------------------------
# Transactions summary
# ------------------------------------------------------------------


def fmt_transactions_summary(data: dict) -> None:
    result = data.get("result", data)

    if isinstance(result, dict):
        table = Table(title="Transactions Summary", show_header=False, border_style="magenta")
        table.add_column("Metric", style="bold", min_width=24)
        table.add_column("Value", justify="right")

        for key, val in result.items():
            if isinstance(val, dict):
                # nested summary (e.g. by status)
                for sub_key, sub_val in val.items():
                    table.add_row(f"  {key} → {sub_key}", str(sub_val))
            else:
                table.add_row(key, str(val))

        console.print(table)
    else:
        console.print_json(data=data)


# ------------------------------------------------------------------
# Refunds list
# ------------------------------------------------------------------


def fmt_refunds(data: dict) -> None:
    result = data.get("result", data)
    rows = []
    if isinstance(result, dict):
        rows = result.get("data", result.get("refunds", []))
    elif isinstance(result, list):
        rows = result

    if not rows:
        console.print("[yellow]No refunds found.[/yellow]")
        return

    table = Table(title="Refunds")
    table.add_column("#", style="dim")
    table.add_column("Refund ID", style="cyan")
    table.add_column("PayU ID")
    table.add_column("Amount", justify="right", style="green")
    table.add_column("Status")
    table.add_column("Date")

    for i, ref in enumerate(rows, 1):
        table.add_row(
            str(i),
            _safe(ref, "refundId", default=_safe(ref, "id")),
            _safe(ref, "payuId", default=_safe(ref, "transactionId")),
            _safe(ref, "amount", default=_safe(ref, "refundAmount")),
            _safe(ref, "status"),
            _safe(ref, "createdOn", default=_safe(ref, "requestedOn")),
        )

    console.print(table)


# ------------------------------------------------------------------
# Refunds summary
# ------------------------------------------------------------------


def fmt_refunds_summary(data: dict) -> None:
    result = data.get("result", data)
    if not isinstance(result, dict):
        console.print_json(data=data)
        return

    table = Table(title="Refunds Summary", show_header=False, border_style="yellow")
    table.add_column("Metric", style="bold", min_width=24)
    table.add_column("Value", justify="right")

    for key, val in result.items():
        if isinstance(val, dict):
            for sub_key, sub_val in val.items():
                table.add_row(f"  {key} → {sub_key}", str(sub_val))
        else:
            table.add_row(key, str(val))
    console.print(table)


# ------------------------------------------------------------------
# Settlement
# ------------------------------------------------------------------


def fmt_settlement(data: dict) -> None:
    result = data.get("result", data)

    if isinstance(result, list):
        table = Table(title="Settlement Details")
        table.add_column("#", style="dim")
        table.add_column("Settlement ID", style="cyan")
        table.add_column("UTR")
        table.add_column("Amount", justify="right", style="green")
        table.add_column("Status")
        table.add_column("Date")

        for i, s in enumerate(result, 1):
            table.add_row(
                str(i),
                _safe(s, "settlementId"),
                _safe(s, "utr"),
                _safe(s, "amount", default=_safe(s, "settledAmount")),
                _safe(s, "status"),
                _safe(s, "settledOn", default=_safe(s, "date")),
            )
        console.print(table)
    elif isinstance(result, dict):
        table = Table(title="Settlement Details", show_header=False, border_style="blue")
        table.add_column("Field", style="bold", min_width=22)
        table.add_column("Value")

        for key, val in result.items():
            if isinstance(val, (dict, list)):
                table.add_row(key, str(val)[:120])
            else:
                table.add_row(key, str(val))
        console.print(table)
    else:
        console.print_json(data=data)


# ------------------------------------------------------------------
# Generic JSON fallback
# ------------------------------------------------------------------

def fmt_json(data: dict) -> None:
    """Fallback: just dump the JSON prettily."""
    console.print_json(data=data)


# ------------------------------------------------------------------
# Error
# ------------------------------------------------------------------

def fmt_error(message: str) -> None:
    console.print(Panel(Text(message, style="red"), title="Error", border_style="red"))
