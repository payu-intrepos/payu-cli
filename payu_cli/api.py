"""
PayU OneAPI HTTP client.

Thin async wrapper over the PayU OneAPI dashboard endpoints.
Returns raw dicts — formatting lives in `payu_cli.formatters`.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any, Iterable, Mapping, Optional

import httpx

from payu_cli.auth import TokenManager

API_BASE = "https://oneapi.payu.in"
TIMEOUT = 30.0

# Mandatory additional fields the dashboard always requests for txn lists.
_TXN_ADDITIONAL_FIELDS = (
    "transactionAmount",
    "transactionCurrency",
    "exchangeRate",
    "exchangeDate",
)

_SSL_ENV_TRUTHY = {"1", "true", "yes", "on"}


def _ssl_verify() -> bool | str:
    """Determine SSL verification setting.

    Priority:
      1. PAYU_NO_VERIFY_SSL=1            → disable verification
      2. PAYU_CA_BUNDLE / SSL_CERT_FILE /
         REQUESTS_CA_BUNDLE (path)       → use custom CA cert
      3. default                          → standard verification
    """
    if os.getenv("PAYU_NO_VERIFY_SSL", "").strip().lower() in _SSL_ENV_TRUTHY:
        return False
    for var in ("PAYU_CA_BUNDLE", "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
        path = os.getenv(var, "").strip()
        if path and os.path.isfile(path):
            return path
    return True


def _default_date_range(days: int = 30) -> tuple[str, str]:
    now = datetime.now()
    return (now - timedelta(days=days)).strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d")


def _build_params(
    scalar: Mapping[str, Any],
    arrays: Iterable[tuple[str, Optional[list[str]]]] = (),
    extra_repeats: Iterable[tuple[str, str]] = (),
) -> list[tuple[str, Any]]:
    """Flatten scalar + list-valued query params into the (k, v) form httpx expects.

    `arrays` is an iterable of (key, values_or_None). Each value becomes its
    own `key=value` pair. `extra_repeats` lets callers append fixed repeated
    pairs (e.g. mandatory additionalFields[]=...).
    """
    pairs: list[tuple[str, Any]] = [
        (k, v) for k, v in scalar.items() if v is not None
    ]
    for key, values in arrays:
        if values:
            pairs.extend((key, v) for v in values)
    pairs.extend(extra_repeats)
    return pairs


class PayUClient:
    """Async HTTP client for the PayU OneAPI dashboard.

    Must be used as an async context manager so the underlying httpx client
    is cleanly closed:

        async with PayUClient(profile) as client:
            data = await client.get_transaction("...")
    """

    def __init__(self, profile: Optional[str] = None):
        self.tm = TokenManager(profile)
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "PayUClient":
        self._client = httpx.AsyncClient(timeout=TIMEOUT, verify=_ssl_verify())
        return self

    async def __aexit__(self, *exc) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Use PayUClient as an async context manager")
        return self._client

    # ------------------------------------------------------------------
    # Low-level request helpers
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Any = None,
        json: Any = None,
    ) -> dict:
        headers = await self.tm.get_oauth_headers(self.client)
        r = await self.client.request(
            method,
            f"{API_BASE}{path}",
            headers=headers,
            params=params,
            json=json,
        )
        r.raise_for_status()
        if not r.content:
            return {}
        return r.json()

    async def _get(self, path: str, *, params: Any = None) -> dict:
        return await self._request("GET", path, params=params)

    async def _post(self, path: str, body: dict) -> dict:
        return await self._request("POST", path, json=body)

    async def _put(self, path: str, body: dict) -> dict:
        return await self._request("PUT", path, json=body)

    # ------------------------------------------------------------------
    # Payment links
    # ------------------------------------------------------------------

    async def create_payment_link(
        self,
        amount: float,
        description: str,
        name: str = "",
        phone: str = "",
        email: str = "",
    ) -> dict:
        # Preserve precision: pass int if amount is a whole number, else float.
        sub_amount: Any = int(amount) if float(amount).is_integer() else amount
        body: dict[str, Any] = {
            "subAmount": sub_amount,
            "description": description,
            "source": "API",
            "isAmountFilledByCustomer": False,
            "viaSms": bool(phone),
            "viaEmail": bool(email),
        }
        customer = {k: v for k, v in (("name", name), ("phone", phone), ("email", email)) if v}
        if customer:
            body["customer"] = customer
        return await self._post("/payment-links", body)

    async def send_payment_link(
        self,
        invoice_number: str,
        *,
        via_email: bool = False,
        via_sms: bool = False,
    ) -> dict:
        return await self._post(
            f"/payment-links/{invoice_number}/share",
            {"invoiceNumber": invoice_number, "viaEmail": via_email, "viaSms": via_sms},
        )

    async def get_payment_link(self, invoice_number: str) -> dict:
        return await self._get(f"/payment-links/{invoice_number}")

    async def list_payment_links(
        self,
        *,
        date_from: str = "",
        date_to: str = "",
        page_offset: int = 0,
        page_size: int = 20,
    ) -> dict:
        if not date_from or not date_to:
            date_from, date_to = _default_date_range()
        return await self._get(
            "/payment-links",
            params={
                "dateFrom": date_from,
                "dateTo": date_to,
                "pageOffset": page_offset,
                "pageSize": page_size,
            },
        )

    async def update_payment_link(
        self,
        invoice_number: str,
        *,
        description: str = "",
        expiry_date: str = "",
        is_active: str = "",
    ) -> dict:
        body = {
            k: v
            for k, v in (
                ("description", description),
                ("expiryDate", expiry_date),
                ("isActive", is_active),
            )
            if v
        }
        return await self._put(f"/payment-links/{invoice_number}", body)

    # ------------------------------------------------------------------
    # Invoices
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
        if not date_from or not date_to:
            date_from, date_to = _default_date_range()
        return await self._get(
            f"/payment-links/{invoice_id}/txns",
            params={
                "dateFrom": date_from,
                "dateTo": date_to,
                "pageOffset": page_offset,
                "pageSize": page_size,
                "order": order,
            },
        )

    # ------------------------------------------------------------------
    # Transactions
    # ------------------------------------------------------------------

    async def get_transaction(self, payu_id: str) -> dict:
        return await self._get(f"/transactions/{payu_id}")

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
        params = _build_params(
            {
                "dateFrom": date_from,
                "dateTo": date_to,
                "all-flag": 1,
                "pageOffset": page_offset,
                "pageLimit": page_limit,
                "minAmount": min_amount,
                "maxAmount": max_amount,
            },
            arrays=[
                ("status[]", status),
                ("mode[]", mode),
                ("paymentSource[]", payment_source),
                ("pa[]", pa),
                ("moreFilters[]", more_filters),
                ("transactionCurrency[]", currency),
            ],
            extra_repeats=[("additionalFields[]", af) for af in _TXN_ADDITIONAL_FIELDS],
        )
        return await self._get("/transactions/", params=params)

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
        params = _build_params(
            {
                "dateFrom": date_from,
                "dateTo": date_to,
                "all-flag": 1,
                "read_refund": "false",
                "minAmount": min_amount,
                "maxAmount": max_amount,
            },
            arrays=[
                ("status", status),
                ("mode", mode),
                ("paymentSource", payment_source),
                ("transactionCurrency", currency),
                ("moreFilters", more_filters),
                ("pa", pa),
            ],
        )
        return await self._get("/transactions/summary/", params=params)

    # ------------------------------------------------------------------
    # Refunds
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
        return await self._get("/refund/v1/onepayu/search", params=params)

    async def refunds_summary(
        self,
        date_from: str,
        date_to: str,
        status: str = "",
    ) -> dict:
        params: dict[str, Any] = {"dateFrom": date_from, "dateTo": date_to}
        if status:
            params["status"] = status
        return await self._get("/refunds/summary/", params=params)

    # ------------------------------------------------------------------
    # Settlements
    # ------------------------------------------------------------------

    async def get_settlement(
        self,
        settlement_id: str,
        *,
        utr: str = "",
        status: str = "inprogress",
        tid: str = "",
    ) -> dict:
        return await self._get(
            "/settlements/details",
            params={
                "settlementId": settlement_id,
                "utr": utr,
                "status": status,
                "tid": tid,
            },
        )

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------

    async def create_report(self, service: str, date_from: str, date_to: str) -> dict:
        return await self._post(
            "/reports",
            {"service": service, "filters": {"dateFrom": date_from, "dateTo": date_to}},
        )

    async def get_report(self, report_id: str) -> dict:
        return await self._get(f"/reports/{report_id}")
