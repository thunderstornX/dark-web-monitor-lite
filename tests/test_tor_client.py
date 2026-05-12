"""Tests for the Tor SOCKS reachability probe."""
from __future__ import annotations

from monitor.tor_client import probe_tor_socks


def test_probe_unreachable_port_returns_false():
    res = probe_tor_socks("socks5://127.0.0.1:65535", timeout_s=0.5)
    assert res.reachable is False
    assert "socks5 connect failed" in res.note


def test_probe_no_url_returns_false():
    res = probe_tor_socks(None)
    assert res.reachable is False
    assert "no Tor SOCKS URL" in res.note


def test_probe_unsupported_scheme_rejects():
    res = probe_tor_socks("http://127.0.0.1:9050")
    assert res.reachable is False
    assert "unsupported scheme" in res.note


def test_probe_unparseable_url_returns_false():
    res = probe_tor_socks("not a url")
    assert res.reachable is False


def test_probe_missing_host_returns_false():
    res = probe_tor_socks("socks5://:9050")
    assert res.reachable is False
    assert "missing host" in res.note


def test_probe_invalid_port_falls_to_default():
    """No port → default 9050, then connect will fail because nothing
    is listening on the test machine."""
    res = probe_tor_socks("socks5://127.0.0.1", timeout_s=0.5)
    # On a CI machine without tor this should fail to connect.
    assert res.reachable is False
