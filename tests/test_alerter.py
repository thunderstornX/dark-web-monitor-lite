"""Tests for the webhook dispatcher."""
from __future__ import annotations

import httpx
import respx

from monitor.alerter import (
    _discord_payload,
    _generic_payload,
    _slack_payload,
    dispatch_alerts,
)
from monitor.findings import AlertStatus, Match, MatchKind


def _sample_matches() -> list[Match]:
    return [
        Match(keyword="AcmeCorp", source_url="http://a",
              kind=MatchKind.EXACT, score=100.0, span="AcmeCorp"),
        Match(keyword="FCo", source_url="http://b",
              kind=MatchKind.FUZZY, score=92.0, span="FCo"),
    ]


# ---------------------------------------------------------------------------
# Payload formatters
# ---------------------------------------------------------------------------

def test_slack_payload_shape():
    p = _slack_payload(_sample_matches())
    assert "blocks" in p
    assert p["blocks"][0]["type"] == "header"


def test_discord_payload_shape():
    p = _discord_payload(_sample_matches())
    assert "content" in p
    assert "AcmeCorp" in p["content"]


def test_discord_payload_handles_zero_matches():
    p = _discord_payload([])
    assert "no matches" in p["content"]


def test_generic_payload_shape():
    p = _generic_payload(_sample_matches())
    assert p["tool"] == "dark-web-monitor-lite"
    assert len(p["matches"]) == 2
    assert p["matches"][0]["keyword"] == "AcmeCorp"
    assert p["matches"][1]["kind"] == "fuzzy"


def test_slack_payload_caps_at_20_entries():
    many = [Match(keyword=f"K{i}", source_url=f"http://x/{i}",
                   kind=MatchKind.EXACT, score=100.0, span=f"K{i}")
             for i in range(50)]
    p = _slack_payload(many)
    # 1 header + 20 sections
    assert len(p["blocks"]) == 21


# ---------------------------------------------------------------------------
# dispatch_alerts
# ---------------------------------------------------------------------------

def test_dispatch_skips_when_no_webhooks(settings_no_tor):
    results = dispatch_alerts(settings_no_tor, _sample_matches())
    assert len(results) == 3
    assert all(r.status == AlertStatus.NO_WEBHOOK for r in results)


def test_dispatch_calls_all_three_when_configured(settings_with_webhooks):
    with respx.mock(assert_all_called=False) as router:
        router.post(settings_with_webhooks.slack_webhook_url).mock(
            return_value=httpx.Response(200, text="ok"))
        router.post(settings_with_webhooks.discord_webhook_url).mock(
            return_value=httpx.Response(204))
        router.post(settings_with_webhooks.generic_webhook_url).mock(
            return_value=httpx.Response(202))
        results = dispatch_alerts(settings_with_webhooks,
                                    _sample_matches())
    targets = [r.target for r in results]
    statuses = [r.status for r in results]
    assert targets == ["slack", "discord", "generic"]
    assert statuses == [AlertStatus.OK, AlertStatus.OK, AlertStatus.OK]


def test_dispatch_records_http_error(settings_with_webhooks):
    with respx.mock(assert_all_called=False) as router:
        router.post(settings_with_webhooks.slack_webhook_url).mock(
            return_value=httpx.Response(500))
        router.post(settings_with_webhooks.discord_webhook_url).mock(
            return_value=httpx.Response(204))
        router.post(settings_with_webhooks.generic_webhook_url).mock(
            return_value=httpx.Response(202))
        results = dispatch_alerts(settings_with_webhooks,
                                    _sample_matches())
    slack = next(r for r in results if r.target == "slack")
    assert slack.status == AlertStatus.HTTP_ERROR
    assert "500" in (slack.note or "")


def test_dispatch_records_network_error(settings_with_webhooks):
    with respx.mock(assert_all_called=False) as router:
        router.post(settings_with_webhooks.slack_webhook_url).mock(
            side_effect=httpx.ConnectError("simulated"))
        router.post(settings_with_webhooks.discord_webhook_url).mock(
            return_value=httpx.Response(204))
        router.post(settings_with_webhooks.generic_webhook_url).mock(
            return_value=httpx.Response(202))
        results = dispatch_alerts(settings_with_webhooks,
                                    _sample_matches())
    slack = next(r for r in results if r.target == "slack")
    assert slack.status == AlertStatus.NETWORK_ERROR
    assert "ConnectError" in (slack.note or "")


def test_dispatch_zero_matches_returns_no_webhook(settings_with_webhooks):
    results = dispatch_alerts(settings_with_webhooks, [])
    assert all(r.status == AlertStatus.NO_WEBHOOK for r in results)
    assert all("nothing to send" in (r.note or "") for r in results)
