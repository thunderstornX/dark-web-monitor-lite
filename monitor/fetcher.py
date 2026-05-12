"""Source fetcher honouring the optional Tor SOCKS proxy.

The fetcher returns a typed FetchResult for every source. Any
failure to reach the Tor proxy short-circuits to
``FetchStatus.TOR_UNAVAILABLE`` for every onion-only URL; clearnet
URLs (https://example.com) are still attempted because the matcher
runs against any text body the operator chooses to feed it. This
keeps the tool useful for clearnet paste-site monitoring even when
no Tor is running.

The body is hashed to a SHA-256 once and discarded immediately
after the matcher runs; only the hash and any matches survive into
the report. This is the data-minimisation default the
ETHICAL_USE.md commits to."""
from __future__ import annotations

import hashlib
import time
from urllib.parse import urlparse

import httpx

from config import Settings
from .findings import FetchResult, FetchStatus
from .matcher import Watchlist, scan_body
from .tor_client import probe_tor_socks


_USER_AGENT = "dark-web-monitor-lite/0.1 (+defensive CTI)"


def _is_onion(url: str) -> bool:
    try:
        host = urlparse(url).hostname or ""
    except Exception:                                       # noqa: BLE001
        return False
    return host.endswith(".onion")


def _build_client(settings: Settings, *, use_tor: bool) -> httpx.Client:
    """Construct an httpx.Client with or without SOCKS5 transport."""
    if use_tor and settings.tor_socks_url:
        # httpx-socks provides a SyncProxyTransport for httpx.
        from httpx_socks import SyncProxyTransport
        transport = SyncProxyTransport.from_url(settings.tor_socks_url)
        return httpx.Client(
            transport=transport,
            timeout=settings.fetch_timeout_s,
            headers={"User-Agent": _USER_AGENT},
            follow_redirects=False,
        )
    return httpx.Client(
        timeout=settings.fetch_timeout_s,
        headers={"User-Agent": _USER_AGENT},
        follow_redirects=False,
    )


def fetch_one(
    settings: Settings,
    url: str,
    watchlist: Watchlist,
    *,
    fuzzy: bool = True,
    threshold: int | None = None,
    client: httpx.Client | None = None,
) -> FetchResult:
    """Fetch one URL and run the matcher against the body.

    Returns ``FetchResult`` with body discarded after matching."""
    threshold = threshold if threshold is not None else settings.fuzzy_threshold

    onion = _is_onion(url)
    if onion:
        probe = probe_tor_socks(settings.tor_socks_url,
                                  timeout_s=2.0)
        if not probe.reachable:
            return FetchResult(
                source_url=url,
                status=FetchStatus.TOR_UNAVAILABLE,
                note=probe.note,
            )

    started = time.perf_counter()
    owns = client is None
    client = client or _build_client(settings, use_tor=onion)
    try:
        try:
            r = client.get(url)
        except httpx.TimeoutException:
            return FetchResult(
                source_url=url,
                status=FetchStatus.TIMEOUT,
                note=f"timeout after {settings.fetch_timeout_s}s",
                elapsed_ms=(time.perf_counter() - started) * 1000.0,
            )
        except httpx.HTTPError as exc:
            return FetchResult(
                source_url=url,
                status=FetchStatus.NETWORK_ERROR,
                note=f"network: {exc.__class__.__name__}",
                elapsed_ms=(time.perf_counter() - started) * 1000.0,
            )

        elapsed = (time.perf_counter() - started) * 1000.0
        if r.status_code >= 400:
            return FetchResult(
                source_url=url,
                status=FetchStatus.HTTP_ERROR,
                http_code=r.status_code,
                note=f"upstream returned HTTP {r.status_code}",
                elapsed_ms=elapsed,
            )

        body = r.text
        body_sha = hashlib.sha256(body.encode("utf-8", "replace")).hexdigest()
        matches = scan_body(body, watchlist,
                              source_url=url,
                              fuzzy=fuzzy, threshold=threshold)
        return FetchResult(
            source_url=url,
            status=FetchStatus.OK,
            http_code=r.status_code,
            elapsed_ms=elapsed,
            body_sha256=body_sha,
            matches=matches,
        )
    finally:
        if owns:
            client.close()
