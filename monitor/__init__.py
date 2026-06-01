"""dark-web-monitor-lite — defensive Tor-aware keyword-watchlist monitor.

Public submodules:
    findings    — cross-module Match / FetchResult / AlertResult / ScanReport
    matcher     — deterministic exact + fuzzy matcher (the measured component)
    tor_client  — standard-library SOCKS-reachability probe with graceful fallback
    fetcher     — httpx + httpx-socks fetcher honouring TOR_SOCKS_URL
    alerter     — Slack / Discord / generic webhook dispatcher
    scheduler   — render a crontab line; or run-once for offline mode
"""
from .findings import (
    AlertResult,
    AlertStatus,
    FetchResult,
    FetchStatus,
    Match,
    MatchKind,
    ScanReport,
)

__all__ = [
    "AlertResult", "AlertStatus",
    "FetchResult", "FetchStatus",
    "Match", "MatchKind",
    "ScanReport",
]
