"""Cross-module dataclasses.

The status taxonomies here are first-class. A defender reading the
report needs to be able to tell ``ran clean`` from ``skipped because
no Tor`` from ``crashed at the network layer``; folding all three
into an empty result list silently misleads. We learned this the
hard way in our companion credential-leak-scanner repo and apply the
same discipline here."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class FetchStatus(str, Enum):
    """Why a fetch produced (or did not produce) a body."""
    OK              = "ok"
    HTTP_ERROR      = "http_error"
    NETWORK_ERROR   = "network_error"
    TOR_UNAVAILABLE = "tor_unavailable"   # SOCKS5 proxy not reachable
    TIMEOUT         = "timeout"
    SKIPPED_POLICY  = "skipped_policy"    # source failed pre-flight


class MatchKind(str, Enum):
    """Whether a match came from the exact or fuzzy matcher branch."""
    EXACT = "exact"
    FUZZY = "fuzzy"


class AlertStatus(str, Enum):
    """Webhook dispatch outcome."""
    OK            = "ok"
    NO_WEBHOOK    = "no_webhook"      # not configured, skipped
    HTTP_ERROR    = "http_error"
    NETWORK_ERROR = "network_error"


@dataclass
class Match:
    """One concrete match between a watchlist keyword and source body."""
    keyword:    str
    source_url: str
    kind:       MatchKind
    score:      float          # 100.0 for exact; rapidfuzz score for fuzzy
    span:       str            # the matched substring (truncated to 80c)


@dataclass
class FetchResult:
    """One source's fetch outcome, body content discarded post-match."""
    source_url:  str
    status:      FetchStatus
    http_code:   int | None = None
    elapsed_ms:  float = 0.0
    body_sha256: str | None = None
    note:        str | None = None
    matches:     list[Match] = field(default_factory=list)


@dataclass
class AlertResult:
    """One alert dispatch outcome."""
    target:    str            # 'slack' | 'discord' | 'generic'
    status:    AlertStatus
    note:      str | None = None
    elapsed_ms: float = 0.0


@dataclass
class ScanReport:
    """Whole-run report the CLI writes to disk."""
    started_at:   str
    finished_at:  str
    fetches:      list[FetchResult] = field(default_factory=list)
    alerts:       list[AlertResult] = field(default_factory=list)
    summary:      dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        for f in d["fetches"]:
            f["status"] = (f["status"].value if hasattr(f["status"], "value")
                            else f["status"])
            for m in f["matches"]:
                m["kind"] = (m["kind"].value if hasattr(m["kind"], "value")
                              else m["kind"])
        for a in d["alerts"]:
            a["status"] = (a["status"].value if hasattr(a["status"], "value")
                            else a["status"])
        return d


def utcnow_iso() -> str:
    """ISO-8601 UTC, second precision."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
