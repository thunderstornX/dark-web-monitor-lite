"""Tor client probe with graceful fallback.

We do **not** import ``stem`` at module load time. Stem is an
optional dependency: a deployer might run the matcher entirely
offline against captured corpora and never need a Tor controller.
A failure to import or connect should produce a typed
``TOR_UNAVAILABLE`` status, never a crash.

The probe used here is the simplest one that catches the common
failure modes: parse the SOCKS5 URL, attempt a TCP connect to the
host:port pair within a short timeout, and report success/failure.
We deliberately do *not* connect to the Tor control port (9051) or
manipulate circuits in this release; circuit rotation is on the
roadmap but is not measured in the current eval, so it would be
dead weight."""
from __future__ import annotations

import socket
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class TorProbeResult:
    reachable: bool
    note: str


def probe_tor_socks(socks_url: str | None,
                     *, timeout_s: float = 2.0) -> TorProbeResult:
    """Probe a SOCKS5 URL for reachability with a short TCP connect.

    Returns ``reachable=False`` on parse, DNS, connect, or timeout
    failure. Never raises."""
    if not socks_url:
        return TorProbeResult(False, "no Tor SOCKS URL configured")
    try:
        parsed = urlparse(socks_url)
    except Exception as exc:                                # noqa: BLE001
        return TorProbeResult(False, f"unparseable url: {exc}")
    if parsed.scheme not in {"socks5", "socks5h"}:
        return TorProbeResult(False,
                              f"unsupported scheme {parsed.scheme!r}")
    host = parsed.hostname or ""
    port = parsed.port or 9050
    if not host:
        return TorProbeResult(False, "missing host")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout_s)
    try:
        s.connect((host, port))
    except (OSError, socket.timeout) as exc:
        return TorProbeResult(False,
                              f"socks5 connect failed: "
                              f"{exc.__class__.__name__}")
    finally:
        s.close()
    return TorProbeResult(True, f"socks5 endpoint {host}:{port} reachable")
