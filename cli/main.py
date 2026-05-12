"""``dark-web-monitor`` -- Click entry point.

Subcommands
-----------

  scan          Run a one-off scan of every source against the watchlist.
  render-cron   Print a crontab line the operator can paste into cron.
  dry-run       Validate watchlist + sources without making any network call.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import click
import yaml

from config import load_settings
from monitor.alerter import dispatch_alerts
from monitor.fetcher import fetch_one
from monitor.findings import ScanReport, utcnow_iso
from monitor.matcher import Watchlist, load_watchlist
from monitor.scheduler import render_cron_line


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _load_watchlist_from_path(path: Path) -> Watchlist:
    raw = _load_yaml(path)
    return load_watchlist(raw)


def _load_sources_from_path(path: Path) -> list[dict]:
    raw = _load_yaml(path)
    sources = raw.get("sources", [])
    if not isinstance(sources, list):
        raise click.UsageError("sources file: 'sources' must be a list")
    pre = raw.get("_global_pre_flight_rules", {})
    if pre.get("requires_auth", False) is True:
        raise click.UsageError(
            "sources file pre-flight: requires_auth=true is rejected.")
    return sources


@click.group()
def cli() -> None:
    """Defensive CTI dark-web monitor (rules-only matcher measured)."""


@cli.command("dry-run")
@click.option("--watchlist", "watchlist_path", required=True,
              type=click.Path(exists=True, path_type=Path))
@click.option("--sources", "sources_path", required=True,
              type=click.Path(exists=True, path_type=Path))
def dry_run(watchlist_path: Path, sources_path: Path) -> None:
    """Validate watchlist + sources without making any network call."""
    watchlist = _load_watchlist_from_path(watchlist_path)
    sources = _load_sources_from_path(sources_path)
    click.echo(f"[+] watchlist: {len(watchlist.keywords)} keyword(s)")
    click.echo(f"[+] sources: {len(sources)} source(s)")
    for s in sources:
        click.echo(f"    - {s.get('name', '?'):<30} {s.get('url', '')}")
    click.echo("[+] dry-run: validations passed; no network calls made.")


@cli.command("scan")
@click.option("--watchlist", "watchlist_path", required=True,
              type=click.Path(exists=True, path_type=Path))
@click.option("--sources", "sources_path", required=True,
              type=click.Path(exists=True, path_type=Path))
@click.option("--output", "output_path", required=True,
              type=click.Path(dir_okay=False, path_type=Path))
@click.option("--no-fuzzy", is_flag=True, default=False,
              help="Disable rapidfuzz matching; exact-only mode.")
@click.option("--threshold", type=int, default=None,
              help="Fuzzy threshold override (default from settings).")
@click.option("--alert/--no-alert", default=True,
              help="Dispatch webhook alerts (default: yes if any "
                   "webhook is configured).")
def scan(
    watchlist_path: Path,
    sources_path: Path,
    output_path: Path,
    no_fuzzy: bool,
    threshold: int | None,
    alert: bool,
) -> None:
    """Run a one-off scan and write a JSON report."""
    settings = load_settings()
    watchlist = _load_watchlist_from_path(watchlist_path)
    sources = _load_sources_from_path(sources_path)

    started_at = utcnow_iso()
    click.echo(f"[*] scan starting at {started_at}")
    click.echo(f"[*] watchlist: {len(watchlist.keywords)} keyword(s); "
               f"sources: {len(sources)}; "
               f"fuzzy={'off' if no_fuzzy else 'on'}")

    fetches = []
    for s in sources:
        url = s.get("url", "")
        if not url:
            continue
        click.echo(f"  · fetching {url}")
        result = fetch_one(
            settings, url, watchlist,
            fuzzy=not no_fuzzy, threshold=threshold,
        )
        fetches.append(result)
        click.echo(f"    [{result.status.value}] hits={len(result.matches)} "
                    f"({result.elapsed_ms:.1f}ms)"
                    + (f"  ({result.note})" if result.note else ""))

    all_matches = [m for f in fetches for m in f.matches]
    alerts = []
    if alert and all_matches:
        click.echo(f"[*] dispatching {len(all_matches)} alert(s)")
        alerts = dispatch_alerts(settings, all_matches)
        for a in alerts:
            click.echo(f"  [{a.status.value}] {a.target}"
                       + (f"  ({a.note})" if a.note else ""))

    summary = {
        "n_sources":    len(fetches),
        "n_ok":         sum(1 for f in fetches if f.status.value == "ok"),
        "n_unavailable": sum(1 for f in fetches
                              if f.status.value == "tor_unavailable"),
        "n_errors":     sum(1 for f in fetches
                             if f.status.value in
                                ("http_error", "network_error", "timeout")),
        "n_matches":    len(all_matches),
        "by_kind": {
            "exact": sum(1 for m in all_matches if m.kind.value == "exact"),
            "fuzzy": sum(1 for m in all_matches if m.kind.value == "fuzzy"),
        },
    }
    report = ScanReport(
        started_at=started_at,
        finished_at=utcnow_iso(),
        fetches=fetches,
        alerts=alerts,
        summary=summary,
    )
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8")
    click.echo(f"[+] wrote {output_path}")
    click.echo(f"[+] {summary['n_matches']} match(es) across "
               f"{summary['n_sources']} source(s)")


@cli.command("render-cron")
@click.option("--schedule", default="0 */6 * * *",
              help="Cron schedule (default: every 6 hours).")
@click.option("--python", "python_exec", default=sys.executable)
@click.option("--repo", "repo_path", default=".",
              type=click.Path(path_type=Path))
@click.option("--watchlist", "watchlist_path", required=True,
              type=click.Path(path_type=Path))
@click.option("--sources", "sources_path", required=True,
              type=click.Path(path_type=Path))
@click.option("--output", "output_path", required=True,
              type=click.Path(path_type=Path))
@click.option("--log", "log_path", required=False,
              type=click.Path(path_type=Path), default=None)
def render_cron(
    schedule: str,
    python_exec: str,
    repo_path: Path,
    watchlist_path: Path,
    sources_path: Path,
    output_path: Path,
    log_path: Path | None,
) -> None:
    """Print a crontab line the operator can paste into their own scheduler."""
    line = render_cron_line(
        schedule=schedule,
        python_executable=python_exec,
        repo_path=repo_path.resolve(),
        watchlist_path=watchlist_path.resolve(),
        sources_path=sources_path.resolve(),
        output_path=output_path.resolve(),
        log_path=log_path.resolve() if log_path else None,
    )
    click.echo(line)


if __name__ == "__main__":
    cli()  # pragma: no cover
