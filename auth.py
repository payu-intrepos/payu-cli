"""
Authentication for PayU OneAPI.

Two auth paths (matching the MCP server behaviour):
  1. OAuth client_credentials → access_token (used for payment-links, invoices)
  2. Direct AUTH_TOKEN bearer     (used for transactions, refunds, settlements)
"""

from __future__ import annotations

import time
from typing import Optional

import httpx

from payu_cli.config import load_profile

OAUTH_URL = "https://accounts.payu.in/oauth/token"
OAUTH_SCOPES = "create_payment_links read_transactions read_payment_links read_invoices"


class TokenManager:
    """Per-session token manager. Caches the OAuth token in memory."""

    def __init__(self, profile: Optional[str] = None):
        creds = load_profile(profile)
        self.client_id: str = creds["client_id"]
        self.client_secret: str = creds["client_secret"]
        self.merchant_id: str = creds["merchant_id"]
        self.auth_token: str = creds["auth_token"]  # direct bearer
        self.env: str = creds["env"]

        # OAuth state
        self._access_token: Optional[str] = None
        self._token_type: str = "Bearer"
        self._expires_at: int = 0

    # ------------------------------------------------------------------
    # OAuth flow
    # ------------------------------------------------------------------

    def _token_expired(self) -> bool:
        return self._access_token is None or time.time() >= (self._expires_at - 300)

    async def _refresh_token(self, client: httpx.AsyncClient) -> None:
        if not self.client_id or not self.client_secret:
            raise RuntimeError(
                "CLIENT_ID / CLIENT_SECRET not configured. "
                "Run `payu config set` or export env vars."
            )

        resp = await client.post(
            OAUTH_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
                "scope": OAUTH_SCOPES,
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        self._access_token = data["access_token"]
        self._token_type = data.get("token_type", "Bearer")
        self._expires_at = int(time.time()) + data.get("expires_in", 3600)

    async def get_oauth_headers(self, client: httpx.AsyncClient) -> dict[str, str]:
        """Headers for endpoints that need OAuth (payment-links, invoices)."""
        if self._token_expired():
            await self._refresh_token(client)
        return {
            "Accept": "application/json",
            "mid": self.merchant_id,
            "Authorization": f"{self._token_type} {self._access_token}",
        }

    # ------------------------------------------------------------------
    # Direct bearer token
    # ------------------------------------------------------------------

    def get_direct_headers(self) -> dict[str, str]:
        """Headers for endpoints that use AUTH_TOKEN (txns, refunds, settlements)."""
        if not self.auth_token:
            raise RuntimeError(
                "AUTH_TOKEN not configured. "
                "Run `payu config set` or export AUTH_TOKEN."
            )
        return {
            "Accept": "application/json",
            "mid": self.merchant_id,
            "Authorization": f"Bearer {self.auth_token}",
        }
