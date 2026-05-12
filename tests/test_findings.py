"""Tests for the cross-module dataclasses + ScanReport JSON shape."""
from __future__ import annotations

import json

from monitor.findings import (
    AlertResult,
    AlertStatus,
    FetchResult,
    FetchStatus,
    Match,
    MatchKind,
    ScanReport,
    utcnow_iso,
)


def test_scan_report_to_dict_serialises_enums():
    fr = FetchResult(
        source_url="http://x",
        status=FetchStatus.OK,
        matches=[Match(keyword="k", source_url="http://x",
                         kind=MatchKind.EXACT, score=100.0, span="k")],
    )
    ar = AlertResult(target="slack", status=AlertStatus.OK)
    report = ScanReport(
        started_at=utcnow_iso(),
        finished_at=utcnow_iso(),
        fetches=[fr], alerts=[ar],
        summary={"n_matches": 1},
    )
    d = report.to_dict()
    json.dumps(d)  # must be JSON-serialisable
    assert d["fetches"][0]["status"] == "ok"
    assert d["fetches"][0]["matches"][0]["kind"] == "exact"
    assert d["alerts"][0]["status"] == "ok"


def test_fetch_status_values():
    assert FetchStatus.OK.value == "ok"
    assert FetchStatus.TOR_UNAVAILABLE.value == "tor_unavailable"


def test_alert_status_values():
    assert AlertStatus.NO_WEBHOOK.value == "no_webhook"


def test_match_kind_values():
    assert MatchKind.EXACT.value == "exact"
    assert MatchKind.FUZZY.value == "fuzzy"


def test_utcnow_iso_format():
    s = utcnow_iso()
    assert s.endswith("+00:00")
    assert "T" in s
