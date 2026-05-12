"""Tests for the fetcher (mocked-only; no live network)."""
from __future__ import annotations

import httpx
import respx

from monitor.fetcher import _is_onion, fetch_one
from monitor.findings import FetchStatus


def test_is_onion_detects_onion_url():
    assert _is_onion("http://abc.onion/x") is True
    assert _is_onion("http://example.com/x") is False
    assert _is_onion("garbage") is False


def test_onion_url_returns_tor_unavailable_when_no_tor(
        settings_no_tor, watchlist):
    """Critical graceful-fallback: onion URL + no Tor = explicit
    TOR_UNAVAILABLE, not a crash."""
    res = fetch_one(settings_no_tor,
                     "http://abc.example.onion/x",
                     watchlist)
    assert res.status == FetchStatus.TOR_UNAVAILABLE
    assert "socks5 connect failed" in (res.note or "")


def test_clearnet_fetch_returns_ok_on_200(settings_no_tor, watchlist):
    url = "https://example.test/page"
    with respx.mock(assert_all_called=False) as router:
        router.get(url).mock(return_value=httpx.Response(
            200, text="AcmeCorp breach disclosed today."))
        res = fetch_one(settings_no_tor, url, watchlist)
    assert res.status == FetchStatus.OK
    assert res.http_code == 200
    assert res.body_sha256 is not None
    assert any(m.keyword == "AcmeCorp" for m in res.matches)


def test_clearnet_fetch_records_http_error(settings_no_tor, watchlist):
    url = "https://example.test/page"
    with respx.mock(assert_all_called=False) as router:
        router.get(url).mock(return_value=httpx.Response(503))
        res = fetch_one(settings_no_tor, url, watchlist)
    assert res.status == FetchStatus.HTTP_ERROR
    assert res.http_code == 503


def test_clearnet_fetch_records_network_error(settings_no_tor, watchlist):
    url = "https://example.test/page"
    with respx.mock(assert_all_called=False) as router:
        router.get(url).mock(side_effect=httpx.ConnectError("boom"))
        res = fetch_one(settings_no_tor, url, watchlist)
    assert res.status == FetchStatus.NETWORK_ERROR
    assert "ConnectError" in (res.note or "")


def test_clearnet_fetch_records_timeout(settings_no_tor, watchlist):
    url = "https://example.test/page"
    with respx.mock(assert_all_called=False) as router:
        router.get(url).mock(side_effect=httpx.ReadTimeout("slow"))
        res = fetch_one(settings_no_tor, url, watchlist)
    assert res.status == FetchStatus.TIMEOUT


def test_clearnet_clean_body_yields_zero_matches(settings_no_tor, watchlist):
    url = "https://example.test/page"
    with respx.mock(assert_all_called=False) as router:
        router.get(url).mock(return_value=httpx.Response(
            200, text="Today's weather forecast is sunny."))
        res = fetch_one(settings_no_tor, url, watchlist)
    assert res.status == FetchStatus.OK
    assert res.matches == []
