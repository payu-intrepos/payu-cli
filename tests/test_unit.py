"""Unit tests — no network, no keyring, no credentials required."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from payu_cli import api, config


# ---------------------------------------------------------------------------
# _build_params — query string assembly
# ---------------------------------------------------------------------------

class TestBuildParams:
    def test_drops_none_scalars(self):
        pairs = api._build_params({"a": 1, "b": None, "c": "x"})
        assert pairs == [("a", 1), ("c", "x")]

    def test_appends_array_values(self):
        pairs = api._build_params(
            {"a": 1},
            arrays=[("s[]", ["a", "b"]), ("m[]", None), ("e[]", [])],
        )
        assert pairs == [("a", 1), ("s[]", "a"), ("s[]", "b")]

    def test_extra_repeats_are_appended(self):
        pairs = api._build_params(
            {"a": 1},
            extra_repeats=[("af[]", "x"), ("af[]", "y")],
        )
        assert pairs == [("a", 1), ("af[]", "x"), ("af[]", "y")]


# ---------------------------------------------------------------------------
# _ssl_verify — env-driven SSL behavior
# ---------------------------------------------------------------------------

class TestSslVerify:
    def test_default_is_true(self, monkeypatch):
        for v in ("PAYU_NO_VERIFY_SSL", "PAYU_CA_BUNDLE", "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
            monkeypatch.delenv(v, raising=False)
        assert api._ssl_verify() is True

    @pytest.mark.parametrize("value", ["1", "true", "YES", "On"])
    def test_disabled_via_env(self, monkeypatch, value):
        monkeypatch.setenv("PAYU_NO_VERIFY_SSL", value)
        assert api._ssl_verify() is False

    def test_custom_ca_bundle(self, monkeypatch, tmp_path):
        ca = tmp_path / "ca.pem"
        ca.write_text("dummy")
        monkeypatch.delenv("PAYU_NO_VERIFY_SSL", raising=False)
        monkeypatch.setenv("PAYU_CA_BUNDLE", str(ca))
        assert api._ssl_verify() == str(ca)

    def test_missing_bundle_path_falls_through(self, monkeypatch, tmp_path):
        monkeypatch.delenv("PAYU_NO_VERIFY_SSL", raising=False)
        monkeypatch.setenv("PAYU_CA_BUNDLE", str(tmp_path / "missing.pem"))
        monkeypatch.delenv("SSL_CERT_FILE", raising=False)
        monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)
        assert api._ssl_verify() is True


# ---------------------------------------------------------------------------
# config read/write — isolation, permissions, malformed JSON
# ---------------------------------------------------------------------------

@pytest.fixture
def isolated_config(monkeypatch, tmp_path):
    cfg_dir = tmp_path / "cfg"
    monkeypatch.setattr(config, "CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(config, "CONFIG_FILE", cfg_dir / "config.json")
    # Disable keyring so secrets land in the file and are testable.
    monkeypatch.setattr(config, "_keyring_set", lambda *_a, **_k: False)
    monkeypatch.setattr(config, "_keyring_get", lambda *_a, **_k: None)
    monkeypatch.setattr(config, "_keyring_delete", lambda *_a, **_k: None)
    for v in ("CLIENT_ID", "CLIENT_SECRET", "MERCHANT_ID", "PAYU_ENV", "PAYU_PROFILE"):
        monkeypatch.delenv(v, raising=False)
    return cfg_dir


class TestConfig:
    def test_roundtrip(self, isolated_config):
        config.save_profile(
            "p1",
            client_id="cid",
            client_secret="csec",
            merchant_id="mid",
            env="test",
        )
        loaded = config.load_profile("p1")
        assert loaded == {
            "profile": "p1",
            "client_id": "cid",
            "client_secret": "csec",
            "merchant_id": "mid",
            "env": "test",
        }

    def test_file_is_chmod_600(self, isolated_config):
        config.save_profile("p1", client_id="cid", client_secret="csec", merchant_id="mid")
        mode = stat.S_IMODE(os.stat(config.CONFIG_FILE).st_mode)
        assert mode == 0o600

    def test_malformed_json_does_not_crash(self, isolated_config):
        config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        config.CONFIG_FILE.write_text("{not valid json")
        # Should ignore corruption and return empty list rather than raise.
        assert config.list_profiles() == []
        # Subsequent save should succeed (and overwrite the corrupt file).
        config.save_profile("fresh", client_id="x", client_secret="y", merchant_id="z")
        assert "fresh" in config.list_profiles()

    def test_delete_missing_profile_is_noop(self, isolated_config):
        # Should not raise.
        config.delete_profile("nope")

    def test_list_and_delete(self, isolated_config):
        config.save_profile("a", client_id="x", client_secret="y", merchant_id="z")
        config.save_profile("b", client_id="x", client_secret="y", merchant_id="z")
        assert sorted(config.list_profiles()) == ["a", "b"]
        config.delete_profile("a")
        assert config.list_profiles() == ["b"]


# ---------------------------------------------------------------------------
# create_payment_link — amount precision
# ---------------------------------------------------------------------------

class TestCreatePaymentLinkAmount:
    @pytest.mark.parametrize("amount,expected", [(100, 100), (100.0, 100), (100.5, 100.5)])
    def test_amount_precision_preserved(self, amount, expected, monkeypatch):
        """A float that's integral must serialize as int; a fractional amount must stay a float."""
        from payu_cli.api import PayUClient

        captured: dict = {}

        async def fake_post(self, path, body):
            captured["body"] = body
            return {}

        monkeypatch.setattr(PayUClient, "_post", fake_post)
        # We never enter the context manager — _post is replaced and TokenManager isn't touched.
        client = PayUClient.__new__(PayUClient)

        import asyncio
        asyncio.run(client.create_payment_link(amount=amount, description="x"))
        assert captured["body"]["subAmount"] == expected
