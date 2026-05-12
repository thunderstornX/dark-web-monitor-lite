"""Shared fixtures."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))

from config import Settings  # noqa: E402
from monitor.matcher import Watchlist, load_watchlist  # noqa: E402


_DISALLOWED_BLOCK = [
    "personal_names",
    "residential_addresses",
    "government_or_military_aliases",
    "journalist_or_activist_identifiers",
    "lawyer_or_litigant_identifiers",
]


@pytest.fixture
def settings_no_tor(monkeypatch) -> Settings:
    """Settings with Tor disabled (unreachable port) and no webhooks."""
    for var in ("TOR_SOCKS_URL", "SLACK_WEBHOOK_URL",
                  "DISCORD_WEBHOOK_URL", "GENERIC_WEBHOOK_URL"):
        monkeypatch.delenv(var, raising=False)
    return Settings(
        tor_socks_url="socks5://127.0.0.1:65535",  # unreachable
        slack_webhook_url=None,
        discord_webhook_url=None,
        generic_webhook_url=None,
        fuzzy_threshold=85,
        fetch_timeout_s=2.0,
        webhook_timeout_s=2.0,
    )


@pytest.fixture
def settings_with_webhooks() -> Settings:
    return Settings(
        tor_socks_url="socks5://127.0.0.1:65535",
        slack_webhook_url="https://hooks.slack.test/services/X/Y/Z",
        discord_webhook_url="https://discord.test/api/webhooks/1/abc",
        generic_webhook_url="https://siem.test/ingest",
        fuzzy_threshold=85,
        webhook_timeout_s=2.0,
    )


@pytest.fixture
def watchlist() -> Watchlist:
    return load_watchlist({
        "brands": ["AcmeCorp", "Acme Corp", "FictionalCo", "FCo"],
        "codenames": ["Project Aurora", "Aurora-Zenith"],
        "iocs": ["acme-prod-secret-id"],
        "_disallowed_categories": _DISALLOWED_BLOCK,
    })
