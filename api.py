"""
PayU OneAPI HTTP client.

Thin wrapper that maps each MCP tool to a method.
Returns raw dicts — formatting is handled by the commands layer.
"""

from __future__ import annotations

from typing import Any, Optional
from urllib.parse import urlencode

import httpx

from payu_cli.auth import TokenManager

API_BASE = "https://oneapi.payu.in"
TIMEOUT = 30.0


class PayUClient:
    def __init__(self, profile: Optional[str] = None):
        self.tm = TokenManager(profile)
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=TIMEOUT)
        return self

    async def __aexit__(self, *exc):
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        assert self._client, "Use PayUClient as an async context manager"
        return self._client

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _get_oauth(self, path: str) -> dict:
        headers = await self.tm.get_oauth_headers(self.client)
        r = await self.client.get(f"{API_BASE}{path}", headers=headers)
        r.raise_for_status()
        return r.json()

    async def _post_oauth(self, path: str, body: dict) -> dict:
        headers = await self.tm.get_oauth_headers(self.client)
        r = await self.client.post(f"{API_BASE}{path}", headers=headers, json=body)
        r.raise_for_status()
        return r.json()

    async def _get_direct(self, path: str) -> dict:
        headers = self.tm.get_direct_headers()
        r = await self.client.get(f"{API_BASE}{path}", headers=headers)
        r.raise_for_status()
        return r.json()

    # ------------------------------------------------------------------
    # Payment links  (OAuth)
    # ------------------------------------------------------------------

    async def create_payment_link(
        self,
        amount: float,
        description: str,
        name: str = "",
        phone: str = "",
        email: str = "",
    ) -> dict:
        body: dict[str, Any] = {
            "subAmount": amount,
            "description": description,
            "source": "payment_link_cli",
            "viaSms": bool(phone),
            "viaEmail": bool(email),
            "customer": {"name": name, "phone": phone, "email": email},
        }
        return await self._post_oauth("/payment-links", body)

    # ------------------------------------------------------------------
    # Invoices  (OAuth)
    # ------------------------------------------------------------------

    async def get_invoice_details(
        self,
        invoice_id: str,
        date_from: str = "",
        date_to: str = "",
        page_offset: int = 0,
        page_size: int = 10,
        order: str = "asc",
    ) -> dict:
        # default date range: last 30 days
        if not date_from or not date_to:
            from datetime import datetime, timedelta

            date_to = datetime.now().strftime("%Y-%m-%d")
            date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        params = urlencode(
            {
                "dateFrom": date_from,
                "dateTo": date_to,
                "pageOffset": page_offset,
                "pageSize": page_size,
                "order": order,
            }
        )
        return await self._get_oauth(f"/payment-links/{invoice_id}/txns?{params}")

    # ------------------------------------------------------------------
    # Transactions  (Direct token)
    # ------------------------------------------------------------------

    async def get_transaction(self, payu_id: str) -> dict:
        return await self._get_oauth(f"/transactions/{payu_id}")

    async def list_transactions(
        self,
        date_from: str,
        date_to: str,
        *,
        page_offset: int = 0,
        page_limit: int = 20,
        status: list[str] | None = None,
        mode: list[str] | None = None,
        payment_source: list[str] | None = None,
        pa: list[str] | None = None,
        more_filters: list[str] | None = None,
        currency: list[str] | None = None,
        min_amount: float | None = None,
        max_amount: float | None = None,
    ) -> dict:
        params: dict[str, Any] = {
            "dateFrom": date_from,
            "dateTo": date_to,
            "all-flag": 1,
            "pageOffset": page_offset,
            "pageLimit": page_limit,
        }
        if min_amount is not None:
            params["minAmount"] = min_amount
        if max_amount is not None:
            params["maxAmount"] = max_amount

        base = urlencode(params)
        array_parts: list[str] = []

        for key, values in [
            ("status[]", status),
            ("mode[]", mode),
            ("paymentSource[]", payment_source),
            ("pa[]", pa),
            ("moreFilters[]", more_filters),
            ("transactionCurrency[]", currency),
        ]:
            if values:
                array_parts.extend(f"{key}={v}" for v in values)

        # mandatory additional fields
        for af in [
            "transactionAmount",
            "transactionCurrency",
            "exchangeRate",
            "exchangeDate",
        ]:
            array_parts.append(f"additionalFields[]={af}")

        qs = f"{base}&{'&'.join(array_parts)}" if array_parts else base
        return await self._get_direct(f"/transactions/?{qs}")

    async def transactions_summary(
        self,
        date_from: str,
        date_to: str,
        *,
        status: list[str] | None = None,
        mode: list[str] | None = None,
        payment_source: list[str] | None = None,
        currency: list[str] | None = None,
        more_filters: list[str] | None = None,
        pa: list[str] | None = None,
        min_amount: float | None = None,
        max_amount: float | None = None,
    ) -> dict:
        params: dict[str, Any] = {
            "dateFrom": date_from,
            "dateTo": date_to,
            "all-flag": 1,
            "read_refund": "false",
        }
        if min_amount is not None:
            params["minAmount"] = min_amount
        if max_amount is not None:
            params["maxAmount"] = max_amount

        base = urlencode(params)
        array_parts: list[str] = []
        for key, values in [
            ("status", status),
            ("mode", mode),
            ("paymentSource", payment_source),
            ("transactionCurrency", currency),
            ("moreFilters", more_filters),
            ("pa", pa),
        ]:
            if values:
                array_parts.extend(f"{key}={v}" for v in values)

        qs = f"{base}&{'&'.join(array_parts)}" if array_parts else base
        return await self._get_direct(f"/transactions/summary/?{qs}")

    # ------------------------------------------------------------------
    # Refunds  (Direct token)
    # ------------------------------------------------------------------

    async def search_refunds(
        self,
        date_from: str,
        date_to: str,
        *,
        page_offset: int = 0,
        page_size: int = 10,
        status: str = "",
    ) -> dict:
        params: dict[str, Any] = {
            "dateFrom": date_from,
            "dateTo": date_to,
            "pageOffset": page_offset,
            "pageSize": page_size,
        }
        if status:
            params["status"] = status
        return await self._get_direct(f"/refund/v1/onepayu/search?{urlencode(params)}")

    async def refunds_summary(
        self,
        date_from: str,
        date_to: str,
        status: str = "",
    ) -> dict:
        params: dict[str, Any] = {"dateFrom": date_from, "dateTo": date_to}
        if status:
            params["status"] = status
        return await self._get_direct(f"/refunds/summary/?{urlencode(params)}")

    # ------------------------------------------------------------------
    # Settlements  (Direct token)
    # ------------------------------------------------------------------

    async def get_settlement(
        self,
        settlement_id: str,
        *,
        utr: str = "",
        status: str = "inprogress",
        tid: str = "",
    ) -> dict:
        params = {
            "settlementId": settlement_id,
            "utr": utr,
            "status": status,
            "tid": tid,
        }
        return await self._get_direct(f"/settlements/details?{urlencode(params)}")
