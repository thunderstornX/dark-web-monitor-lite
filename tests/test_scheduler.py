"""Tests for the scheduler stub."""
from __future__ import annotations

from pathlib import Path

from monitor.scheduler import render_cron_line


def test_render_cron_line_basic():
    line = render_cron_line(
        schedule="0 */6 * * *",
        python_executable="/usr/bin/python3",
        repo_path=Path("/srv/dwm"),
        watchlist_path=Path("/srv/dwm/config/watchlist.yaml"),
        sources_path=Path("/srv/dwm/config/sources.yaml"),
        output_path=Path("/srv/dwm/out/scan.json"),
    )
    assert line.startswith("0 */6 * * *  cd /srv/dwm && ")
    assert "-m cli.main scan" in line
    assert "--watchlist /srv/dwm/config/watchlist.yaml" in line
    assert "--sources /srv/dwm/config/sources.yaml" in line
    assert "--output /srv/dwm/out/scan.json" in line


def test_render_cron_line_quotes_spaces_in_paths():
    line = render_cron_line(
        schedule="*/15 * * * *",
        python_executable="/usr/bin/python3",
        repo_path=Path("/srv/with space"),
        watchlist_path=Path("/srv/with space/wl.yaml"),
        sources_path=Path("/srv/with space/src.yaml"),
        output_path=Path("/srv/with space/out.json"),
    )
    assert "'/srv/with space'" in line
    assert "'/srv/with space/wl.yaml'" in line


def test_render_cron_line_appends_log_redirect():
    line = render_cron_line(
        schedule="0 0 * * *",
        python_executable="/usr/bin/python3",
        repo_path=Path("/r"),
        watchlist_path=Path("/r/wl.yaml"),
        sources_path=Path("/r/src.yaml"),
        output_path=Path("/r/out.json"),
        log_path=Path("/var/log/dwm.log"),
    )
    assert ">> /var/log/dwm.log" in line
    assert "2>&1" in line
