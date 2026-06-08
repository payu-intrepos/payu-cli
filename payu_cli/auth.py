"""
Authentication for PayU OneAPI.

Uses OAuth client_credentials to mint a short-lived access token from
the configured client_id + client_secret. The token is cached in memory
for the lifetime of the process.
"""

from __future__ import annotations

import time
from typing import Optional

import httpx

from payu_cli.config import load_profile

OAUTH_URL = "https://accounts.payu.in/oauth/token"
OAUTH_SCOPES = (
    "create_payment_links read_transactions read_payment_links "
    "read_invoices update_payment_links"
)

# Refresh `EXPIRY_SKEW` seconds before the token actually expires so that
# in-flight requests don't race the expiry boundary.
EXPIRY_SKEW = 300
DEFAULT_LIFETIME = 3600


class TokenManager:
    """Per-session token manager. Caches the OAuth token in memory."""

    def __init__(self, profile: Optional[str] = None):
        creds = load_profile(profile)
        self.client_id: str = creds["client_id"]
        self.client_secret: str = creds["client_secret"]
        self.merchant_id: str = creds["merchant_id"]
        self.env: str = creds["env"]

        self._access_token: Optional[str] = None
        self._token_type: str = "Bearer"
        self._expires_at: float = 0.0

    def _token_expired(self) -> bool:
        return self._access_token is None or time.time() >= (self._expires_at - EXPIRY_SKEW)

    async def _refresh_token(self, client: httpx.AsyncClient) -> None:
        if not self.client_id or not self.client_secret:
            raise RuntimeError(
                "client_id / client_secret not configured. "
                "Run `payu config set` or export CLIENT_ID / CLIENT_SECRET."
            )

        try:
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
        except httpx.RequestError as e:
            raise RuntimeError(f"OAuth request failed: {e}") from e

        if resp.status_code >= 400:
            body = resp.text.strip() or "<empty body>"
            raise RuntimeError(
                f"OAuth token request rejected ({resp.status_code}): {body}"
            )

        try:
            data = resp.json()
        except ValueError as e:
            raise RuntimeError(f"OAuth response was not JSON: {resp.text[:200]}") from e

        try:
            self._access_token = data["access_token"]
        except KeyError as e:
            raise RuntimeError(f"OAuth response missing access_token: {data}") from e

        self._token_type = data.get("token_type", "Bearer")
        self._expires_at = time.time() + int(data.get("expires_in", DEFAULT_LIFETIME))

    async def get_oauth_headers(self, client: httpx.AsyncClient) -> dict[str, str]:
        """Headers for all PayU OneAPI endpoints."""
        if self._token_expired():
            await self._refresh_token(client)
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "mid": self.merchant_id,
            "merchantId": self.merchant_id,
            "Authorization": f"{self._token_type} {self._access_token}",
        }
