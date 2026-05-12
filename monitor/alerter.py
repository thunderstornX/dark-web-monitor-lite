"""Webhook dispatcher for Slack, Discord, and generic HTTP POST.

Each provider expects a slightly different JSON shape; we keep all
three formatters in this module rather than splitting per-provider
files because the formats are short and the per-provider drift is
small. Webhook URLs are injected via ``Settings`` and never logged
or echoed back into the alert payload — secret hygiene at module
boundary."""
from __future__ import annotations

import time
from typing import Iterable

import httpx

from config import Settings
from .findings import AlertResult, AlertStatus, Match


# ---------------------------------------------------------------------------
# Per-provider formatters
# ---------------------------------------------------------------------------

def _slack_payload(matches: list[Match]) -> dict:
    """Slack incoming-webhook payload."""
    blocks = []
    blocks.append({
        "type": "header",
        "text": {"type": "plain_text",
                  "text": f"dark-web-monitor: {len(matches)} match(es)"},
    })
    # Hard cap the Slack payload at 20 entries; longer is unreadable.
    for m in matches[:20]:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (f"*{m.keyword}* (`{m.kind.value}`, "
                         f"score `{m.score:.1f}`)\n"
                         f"`{m.span}`\n"
                         f"<{m.source_url}>"),
            },
        })
    return {"blocks": blocks}


def _discord_payload(matches: list[Match]) -> dict:
    """Discord webhook payload."""
    if not matches:
        return {"content": "dark-web-monitor: no matches in scan."}
    lines = [f"**dark-web-monitor:** {len(matches)} match(es)"]
    for m in matches[:20]:
        lines.append(
            f"- **{m.keyword}** ({m.kind.value}, "
            f"score {m.score:.1f}): `{m.span}` <{m.source_url}>")
    return {"content": "\n".join(lines)}


def _generic_payload(matches: list[Match]) -> dict:
    """Generic HTTP-POST JSON payload — flat, easy for Sentinel/SIEM."""
    return {
        "tool":     "dark-web-monitor-lite",
        "version":  "0.1.0",
        "matches":  [
            {
                "keyword":    m.keyword,
                "source":     m.source_url,
                "kind":       m.kind.value,
                "score":      m.score,
                "span":       m.span,
            }
            for m in matches
        ],
    }


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def _post(
    url: str | None,
    payload: dict,
    target: str,
    *,
    timeout_s: float,
    client: httpx.Client | None,
) -> AlertResult:
    if not url:
        return AlertResult(
            target=target,
            status=AlertStatus.NO_WEBHOOK,
            note=f"{target} webhook not configured; skipped",
        )
    started = time.perf_counter()
    owns = client is None
    client = client or httpx.Client(timeout=timeout_s)
    try:
        try:
            r = client.post(url, json=payload)
        except httpx.HTTPError as exc:
            return AlertResult(
                target=target,
                status=AlertStatus.NETWORK_ERROR,
                note=f"network: {exc.__class__.__name__}",
                elapsed_ms=(time.perf_counter() - started) * 1000.0,
            )
        elapsed = (time.perf_counter() - started) * 1000.0
        if r.status_code >= 400:
            return AlertResult(
                target=target,
                status=AlertStatus.HTTP_ERROR,
                note=f"{target} returned HTTP {r.status_code}",
                elapsed_ms=elapsed,
            )
        return AlertResult(
            target=target,
            status=AlertStatus.OK,
            elapsed_ms=elapsed,
        )
    finally:
        if owns:
            client.close()


def dispatch_alerts(
    settings: Settings,
    matches: Iterable[Match],
    *,
    client: httpx.Client | None = None,
) -> list[AlertResult]:
    """Dispatch alerts to every configured webhook.

    Returns one AlertResult per provider regardless of whether the
    provider is configured — operators see coverage gaps in the
    report itself rather than wondering why an alert never arrived."""
    matches = list(matches)
    if not matches:
        # Even with zero matches, surface the dispatch decision.
        return [
            AlertResult(target="slack",
                          status=AlertStatus.NO_WEBHOOK,
                          note="no matches; nothing to send"),
            AlertResult(target="discord",
                          status=AlertStatus.NO_WEBHOOK,
                          note="no matches; nothing to send"),
            AlertResult(target="generic",
                          status=AlertStatus.NO_WEBHOOK,
                          note="no matches; nothing to send"),
        ]
    results: list[AlertResult] = []
    results.append(_post(settings.slack_webhook_url,
                          _slack_payload(matches),
                          "slack",
                          timeout_s=settings.webhook_timeout_s,
                          client=client))
    results.append(_post(settings.discord_webhook_url,
                          _discord_payload(matches),
                          "discord",
                          timeout_s=settings.webhook_timeout_s,
                          client=client))
    results.append(_post(settings.generic_webhook_url,
                          _generic_payload(matches),
                          "generic",
                          timeout_s=settings.webhook_timeout_s,
                          client=client))
    return results
