"""
Credential and configuration management.

Resolution order:
  1. Explicit --profile flag
  2. PAYU_PROFILE env var
  3. "default" profile

Credentials are stored in ~/.config/payu-cli/config.json (mode 0600).
The client_secret goes into the OS keyring when available, falling back to
plaintext in the config file with a warning.
"""

from __future__ import annotations

import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console(stderr=True)

CONFIG_DIR = Path.home() / ".config" / "payu-cli"
CONFIG_FILE = CONFIG_DIR / "config.json"

KEYRING_SERVICE = "payu-cli"


# ---------------------------------------------------------------------------
# Low-level read / write
# ---------------------------------------------------------------------------

def _read_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text() or "{}")
    except json.JSONDecodeError as e:
        console.print(
            f"[yellow]⚠  config file is corrupted ({e.msg} at line {e.lineno}); "
            f"ignoring and starting fresh. Existing file: {CONFIG_FILE}[/yellow]"
        )
        return {}


def _write_config(data: dict) -> None:
    """Atomically write the config file with secure permissions.

    Writes to a temp file in the same directory then renames, avoiding any
    window where the file exists with default permissions.
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".config.", dir=CONFIG_DIR)
    try:
        os.fchmod(fd, stat.S_IRUSR | stat.S_IWUSR)  # 0600 before any write
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, CONFIG_FILE)
    except Exception:
        # Best-effort cleanup if rename never happened.
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Keyring helpers
# ---------------------------------------------------------------------------

def _keyring_set(service: str, key: str, value: str) -> bool:
    """Store a secret in the OS keyring. Returns False if keyring is unusable."""
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

    if not _keyring_set(KEYRING_SERVICE, f"{profile}:client_secret", client_secret):
        profiles[profile]["client_secret"] = client_secret
        console.print(
            "[yellow]⚠  keyring unavailable — client_secret stored in plaintext config[/yellow]"
        )

    _write_config(cfg)
    console.print(f"[green]✓[/green] Profile [bold]{profile}[/bold] saved")


def load_profile(profile: Optional[str] = None) -> dict:
    """Load credentials for the given profile.

    Falls back to environment variables when no profile config exists:
      CLIENT_ID, CLIENT_SECRET, MERCHANT_ID, PAYU_ENV
    """
    name = profile or active_profile_name()
    cfg = _read_config()
    p = cfg.get("profiles", {}).get(name, {})

    client_secret = (
        _keyring_get(KEYRING_SERVICE, f"{name}:client_secret")
        or p.get("client_secret")
        or os.getenv("CLIENT_SECRET", "")
    )

    return {
        "profile": name,
        "client_id": p.get("client_id") or os.getenv("CLIENT_ID", ""),
        "client_secret": client_secret,
        "merchant_id": p.get("merchant_id") or os.getenv("MERCHANT_ID", ""),
        "env": p.get("env") or os.getenv("PAYU_ENV", "production"),
    }


def list_profiles() -> list[str]:
    return list(_read_config().get("profiles", {}).keys())


def delete_profile(profile: str) -> None:
    cfg = _read_config()
    if cfg.get("profiles", {}).pop(profile, None) is None:
        console.print(f"[yellow]Profile [bold]{profile}[/bold] does not exist[/yellow]")
        return
    _write_config(cfg)
    _keyring_delete(KEYRING_SERVICE, f"{profile}:client_secret")
    console.print(f"[green]✓[/green] Profile [bold]{profile}[/bold] deleted")
