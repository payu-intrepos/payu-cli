#!/usr/bin/env python3
"""
Integration tests for payu-cli — runs every command against live PayU APIs.

Every API command MUST exit 0. If a test fails, the API or CLI is broken and needs fixing.

Prerequisites:
    1. Configure credentials:  payu config set
    2. pip install pytest

Run:
    pytest tests/test_integration.py -v --tb=short
    pytest tests/test_integration.py -v -k "TestTransactions"
    PAYU_TEST_PROFILE=staging pytest tests/test_integration.py -v
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time

import pytest

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PROFILE = os.getenv("PAYU_TEST_PROFILE", None)
PROFILE_FLAG = ["--profile", PROFILE] if PROFILE else []

from datetime import datetime, timedelta

_now = datetime.now()
DATE_TO = _now.strftime("%Y-%m-%d 23:59:59")
DATE_FROM = (_now - timedelta(days=30)).strftime("%Y-%m-%d 00:00:00")
DATE_TO_SHORT = _now.strftime("%Y-%m-%d")
DATE_FROM_SHORT = (_now - timedelta(days=30)).strftime("%Y-%m-%d")

TEST_PROFILE = "test_ci_temp"


def run(args: list[str], *, should_fail: bool = False) -> subprocess.CompletedProcess:
    """Run `payu <args>` and assert exit 0 (unless should_fail)."""
    cmd = [sys.executable, "-m", "payu_cli.main"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if not should_fail:
        assert result.returncode == 0, (
            f"\n{'='*60}\n"
            f"COMMAND FAILED: payu {' '.join(args)}\n"
            f"EXIT CODE: {result.returncode}\n"
            f"{'='*60}\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}\n"
            f"{'='*60}"
        )
    return result


def run_help(args: list[str]) -> subprocess.CompletedProcess:
    """Run a no-args command that shows help. Typer/Click may exit 0 or 2."""
    cmd = [sys.executable, "-m", "payu_cli.main"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    assert result.returncode in (0, 2), (
        f"Help command unexpected exit {result.returncode}: payu {' '.join(args)}\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    return result


# ===================================================================
# Version
# ===================================================================

class TestVersion:
    def test_version(self):
        from payu_cli import __version__
        r = run(["version"])
        assert __version__ in r.stdout


# ===================================================================
# Config commands (local only, no API)
# ===================================================================

class TestConfig:
    def test_01_set(self):
        r = run([
            "config", "set",
            "--profile", TEST_PROFILE,
            "--client-id", "test_cid_123",
            "--client-secret", "test_secret_456",
            "--merchant-id", "test_mid_789",
            "--env", "test",
        ])
        output = r.stdout + r.stderr
        assert "saved" in output.lower()

    def test_02_show(self):
        r = run(["config", "show", "--profile", TEST_PROFILE])
        output = r.stdout + r.stderr
        assert "test_cid_123" in output
        assert "test_mid_789" in output

    def test_03_list(self):
        r = run(["config", "list"])
        output = r.stdout + r.stderr
        assert TEST_PROFILE in output

    def test_04_delete(self):
        r = run(["config", "delete", TEST_PROFILE])
        output = r.stdout + r.stderr
        assert "deleted" in output.lower()

    def test_05_show_default(self):
        r = run(["config", "show"] + PROFILE_FLAG)
        assert r.returncode == 0


# ===================================================================
# Account commands (local only, no API)
# ===================================================================

class TestAccount:
    def test_01_add(self):
        run([
            "account", "add",
            "--profile", TEST_PROFILE,
            "--client-id", "acct_cid",
            "--client-secret", "acct_secret",
            "--merchant-id", "acct_mid",
        ])

    def test_02_list(self):
        r = run(["account", "list"])
        assert TEST_PROFILE in (r.stdout + r.stderr)

    def test_03_show(self):
        r = run(["account", "show", "--profile", TEST_PROFILE])
        assert "acct_cid" in (r.stdout + r.stderr)

    def test_04_switch(self):
        r = run(["account", "switch", TEST_PROFILE])
        assert "PAYU_PROFILE" in (r.stdout + r.stderr)

    def test_05_remove(self):
        r = run(["account", "remove", TEST_PROFILE])
        assert "deleted" in (r.stdout + r.stderr).lower()


# ===================================================================
# Payment Links — MUST all succeed against real API
# ===================================================================

_payment_state: dict = {}


class TestPaymentLinks:
    def test_01_create_link(self):
        r = run([
            "pay", "create-link",
            "--amount", "100",
            "--desc", "CI Test Payment",
            "--name", "Test User",
            "--email", "test@example.com",
        ] + PROFILE_FLAG)
        output = r.stdout + r.stderr
        # Extract invoice number from Rich table output
        # Table row looks like: │ Invoice #  │ INV_xxxxx │
        match = re.search(r"Invoice\s*#?\s*│\s*(\S+)", output)
        if not match:
            match = re.search(r'"invoiceNumber"\s*:\s*"([^"]+)"', output)
        if match:
            inv = match.group(1).strip("\"', │")
            if len(inv) > 2:
                _payment_state["invoice_number"] = inv
        # Verify we actually got a link created
        assert "Payment Link Created" in output or "invoiceNumber" in output, \
            f"Payment link creation didn't return expected output:\n{output}"

    def test_02_list_links(self):
        run(["pay", "list", "--limit", "5"] + PROFILE_FLAG)

    def test_03_status(self):
        inv = _payment_state.get("invoice_number")
        if not inv:
            pytest.skip("No invoice number from create-link")
        run(["pay", "status", inv] + PROFILE_FLAG)

    def test_04_update(self):
        inv = _payment_state.get("invoice_number")
        if not inv:
            pytest.skip("No invoice number from create-link")
        run(["pay", "update", inv, "--desc", "CI Test Updated"] + PROFILE_FLAG)

    def test_05_send_email(self):
        inv = _payment_state.get("invoice_number")
        if not inv:
            pytest.skip("No invoice number from create-link")
        run(["pay", "send", inv, "--email"] + PROFILE_FLAG)

    def test_06_invoice(self):
        inv = _payment_state.get("invoice_number")
        if not inv:
            pytest.skip("No invoice number from create-link")
        run(["pay", "invoice", inv] + PROFILE_FLAG)


# ===================================================================
# Transactions — MUST all succeed against real API
# ===================================================================

_txn_state: dict = {}


class TestTransactions:
    def test_01_list(self):
        r = run([
            "txn", "list",
            "--from", DATE_FROM,
            "--to", DATE_TO,
            "--limit", "5",
        ] + PROFILE_FLAG)
        output = r.stdout + r.stderr
        # Grab a PayU ID (15-20 digit number) for the get test
        match = re.search(r"\b(\d{15,20})\b", output)
        if match:
            _txn_state["payu_id"] = match.group(1)

    def test_02_list_with_status_filter(self):
        run([
            "txn", "list",
            "--from", DATE_FROM,
            "--to", DATE_TO,
            "--status", "captured",
            "--limit", "3",
        ] + PROFILE_FLAG)

    def test_03_list_with_amount_filter(self):
        run([
            "txn", "list",
            "--from", DATE_FROM,
            "--to", DATE_TO,
            "--min-amount", "100",
            "--max-amount", "50000",
            "--limit", "3",
        ] + PROFILE_FLAG)

    def test_04_summary(self):
        run([
            "txn", "summary",
            "--from", DATE_FROM,
            "--to", DATE_TO,
        ] + PROFILE_FLAG)

    def test_05_summary_with_filters(self):
        run([
            "txn", "summary",
            "--from", DATE_FROM,
            "--to", DATE_TO,
            "--status", "captured",
            "--mode", "UPI",
        ] + PROFILE_FLAG)

    def test_06_get(self):
        pid = _txn_state.get("payu_id")
        if not pid:
            pytest.skip("No transaction ID found from list — maybe no txns in last 30 days")
        run(["txn", "get", pid] + PROFILE_FLAG)

    def test_07_amount_validation_rejects_unpaired(self):
        """--min-amount without --max-amount must fail."""
        r = run([
            "txn", "list",
            "--from", DATE_FROM,
            "--to", DATE_TO,
            "--min-amount", "100",
        ] + PROFILE_FLAG, should_fail=True)
        assert r.returncode != 0


# ===================================================================
# Refunds — MUST all succeed against real API
# ===================================================================

class TestRefunds:
    def test_01_search(self):
        run([
            "refund", "search",
            "--from", DATE_FROM_SHORT,
            "--to", DATE_TO_SHORT,
            "--limit", "5",
        ] + PROFILE_FLAG)

    def test_02_search_with_status(self):
        run([
            "refund", "search",
            "--from", DATE_FROM_SHORT,
            "--to", DATE_TO_SHORT,
            "--status", "success",
        ] + PROFILE_FLAG)

    @pytest.mark.xfail(reason="Requires 'read_refunds' OAuth scope — enable in PayU dashboard")
    def test_03_summary(self):
        run([
            "refund", "summary",
            "--from", DATE_FROM_SHORT,
            "--to", DATE_TO_SHORT,
        ] + PROFILE_FLAG)

    def test_04_invalid_status_rejected(self):
        r = run([
            "refund", "search",
            "--from", DATE_FROM_SHORT,
            "--to", DATE_TO_SHORT,
            "--status", "bogus",
        ] + PROFILE_FLAG, should_fail=True)
        assert r.returncode != 0


# ===================================================================
# Settlements — uses a real settlement ID if available
# ===================================================================

class TestSettlements:
    def test_01_get_with_placeholder(self):
        """Settlement get with a fake ID — API will return an error, CLI should handle it cleanly."""
        r = run([
            "settlement", "get", "SETTLE_TEST_001",
        ] + PROFILE_FLAG, should_fail=True)
        output = r.stdout + r.stderr
        # Must not crash with a Python traceback
        assert "Traceback (most recent call last)" not in output, \
            f"CLI crashed with traceback:\n{output}"


# ===================================================================
# Reports — MUST all succeed against real API
# ===================================================================

_report_state: dict = {}


class TestReports:
    @pytest.mark.xfail(reason="Requires 'create_reports' OAuth scope — enable in PayU dashboard")
    def test_01_create_transactions(self):
        r = run([
            "report", "create", "transactions",
            "--from", DATE_FROM,
            "--to", DATE_TO,
        ] + PROFILE_FLAG)
        output = r.stdout
        # Extract report ID for get test
        match = re.search(r'"id"\s*:\s*"([^"]+)"', output)
        if not match:
            match = re.search(r'"reportId"\s*:\s*"([^"]+)"', output)
        if match:
            _report_state["report_id"] = match.group(1)

    def test_02_create_invalid_service_rejected(self):
        r = run([
            "report", "create", "bogus_service",
            "--from", DATE_FROM,
            "--to", DATE_TO,
        ] + PROFILE_FLAG, should_fail=True)
        assert r.returncode != 0

    @pytest.mark.xfail(reason="Requires 'read_reports' OAuth scope — enable in PayU dashboard")
    def test_03_get_report(self):
        rid = _report_state.get("report_id")
        if not rid:
            pytest.skip("No report ID from create")
        time.sleep(3)  # give the report a moment to generate
        run(["report", "get", rid] + PROFILE_FLAG)


# ===================================================================
# Help / No-args behavior
# ===================================================================

class TestHelpAndUsage:
    def test_root_help(self):
        r = run_help([])
        assert "pay" in (r.stdout + r.stderr).lower()

    def test_pay_no_args(self):
        r = run_help(["pay"])
        assert "create-link" in (r.stdout + r.stderr)

    def test_txn_no_args(self):
        r = run_help(["txn"])
        output = r.stdout + r.stderr
        assert "get" in output or "list" in output

    def test_refund_no_args(self):
        r = run_help(["refund"])
        output = r.stdout + r.stderr
        assert "search" in output or "summary" in output

    def test_config_no_args(self):
        r = run_help(["config"])
        output = r.stdout + r.stderr
        assert "set" in output or "show" in output

    def test_account_no_args(self):
        r = run_help(["account"])
        output = r.stdout + r.stderr
        assert "list" in output or "add" in output

    def test_report_no_args(self):
        r = run_help(["report"])
        output = r.stdout + r.stderr
        assert "create" in output or "get" in output

    def test_settlement_no_args(self):
        r = run_help(["settlement"])
        output = r.stdout + r.stderr
        assert "get" in output or "Usage" in output
