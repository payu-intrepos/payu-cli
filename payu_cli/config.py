"""
Credential and configuration management.

Resolution order:
  1. Explicit --profile flag
  2. PAYU_PROFILE env var
  3. "default" profile

Credentials are stored in ~/.config/payu-cli/config.json
Secrets (client_secret, auth_token) go into the OS keyring when available,
falling back to plaintext in the config file with a warning.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console(stderr=True)

CONFIG_DIR = Path.home() / ".config" / "payu-cli"
CONFIG_FILE = CONFIG_DIR / "config.json"


# ---------------------------------------------------------------------------
# Low-level read / write
# ---------------------------------------------------------------------------

def _read_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


def _write_config(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2))
    # restrict permissions
    CONFIG_FILE.chmod(0o600)


# ---------------------------------------------------------------------------
# Keyring helpers
# ---------------------------------------------------------------------------

def _keyring_set(service: str, key: str, value: str) -> bool:
    """Try to store a secret in the OS keyring. Returns False on failure."""
    try:
        import keyring as kr
        kr.set_password(service, key, value)
        return True
    except Exception:
        return False


def _keyring_get(service: str, key: str) -> Optional[str]:
    try:
        import keyring as kr
        return kr.get_password(service, key)
    except Exception:
        return None


def _keyring_delete(service: str, key: str) -> None:
    try:
        import keyring as kr
        kr.delete_password(service, key)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

KEYRING_SERVICE = "payu-cli"


def active_profile_name() -> str:
    return os.getenv("PAYU_PROFILE", "default")


def save_profile(
    profile: str,
    *,
    client_id: str,
    client_secret: str,
    merchant_id: str,
    env: str = "production",
) -> None:
    """Persist a named credential profile."""
    cfg = _read_config()
    profiles = cfg.setdefault("profiles", {})
    profiles[profile] = {
        "client_id": client_id,
        "merchant_id": merchant_id,
        "env": env,
    }

    # Try keyring first; fall back to config file
    stored_secret = _keyring_set(KEYRING_SERVICE, f"{profile}:client_secret", client_secret)
    if not stored_secret:
        profiles[profile]["client_secret"] = client_secret
        console.print(
            "[yellow]⚠  keyring unavailable — client_secret stored in plaintext config[/yellow]"
        )

    _write_config(cfg)
    console.print(f"[green]✓[/green] Profile [bold]{profile}[/bold] saved")


def load_profile(profile: Optional[str] = None) -> dict:
    """
    Load credentials for the given profile.

    Falls back to environment variables if no profile config exists:
      CLIENT_ID, CLIENT_SECRET, AUTH_TOKEN, MERCHANT_ID
    """
    name = profile or active_profile_name()
    cfg = _read_config()
    p = cfg.get("profiles", {}).get(name, {})

    client_id = p.get("client_id") or os.getenv("CLIENT_ID", "")
    merchant_id = p.get("merchant_id") or os.getenv("MERCHANT_ID", "")
    env = p.get("env", os.getenv("PAYU_ENV", "production"))

    # Secrets: keyring → config file → env var
    client_secret = (
        _keyring_get(KEYRING_SERVICE, f"{name}:client_secret")
        or p.get("client_secret")
        or os.getenv("CLIENT_SECRET", "")
    )

    return {
        "profile": name,
        "client_id": client_id,
        "client_secret": client_secret,
        "merchant_id": merchant_id,
        "env": env,
    }


def list_profiles() -> list[str]:
    cfg = _read_config()
    return list(cfg.get("profiles", {}).keys())


def delete_profile(profile: str) -> None:
    cfg = _read_config()
    cfg.get("profiles", {}).pop(profile, None)
    _write_config(cfg)
    _keyring_delete(KEYRING_SERVICE, f"{profile}:client_secret")
    console.print(f"[green]✓[/green] Profile [bold]{profile}[/bold] deleted")
