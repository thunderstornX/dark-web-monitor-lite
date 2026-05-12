"""Scheduling stub.

We intentionally do not bind the ``python-crontab`` package as a hard
dependency at this stage. python-crontab manipulates the host's
crontab file, and asking the tool to do so by default is a posture
we would rather an operator opt into deliberately.

This module instead emits a *crontab line* the operator can paste
into their own scheduler (cron, systemd timer, Kubernetes CronJob).
For ad-hoc one-off runs the CLI provides ``--run-once`` which calls
the scan path directly without any scheduler involvement."""
from __future__ import annotations

import shlex
from pathlib import Path


def render_cron_line(
    *,
    schedule: str,
    python_executable: str,
    repo_path: Path,
    watchlist_path: Path,
    sources_path: Path,
    output_path: Path,
    log_path: Path | None = None,
) -> str:
    """Build a crontab-format line for the operator to install.

    We keep the rendering pure so tests can pin the output exactly.
    The command is constructed using :func:`shlex.quote` on every
    interpolated path so a path containing whitespace cannot escape
    the line."""
    parts = [
        shlex.quote(python_executable),
        "-m",
        "cli.main",
        "scan",
        "--watchlist", shlex.quote(str(watchlist_path)),
        "--sources",   shlex.quote(str(sources_path)),
        "--output",    shlex.quote(str(output_path)),
    ]
    cmd = " ".join(parts)
    if log_path is not None:
        cmd = f"({cmd}) >> {shlex.quote(str(log_path))} 2>&1"
    return f"{schedule}  cd {shlex.quote(str(repo_path))} && {cmd}"
