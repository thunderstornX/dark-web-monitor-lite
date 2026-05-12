<!-- markdownlint-disable MD033 MD041 -->

```
  ██████╗ ██╗    ██╗███╗   ███╗
  ██╔══██╗██║    ██║████╗ ████║      dark-web-monitor-lite
  ██║  ██║██║ █╗ ██║██╔████╔██║
  ██║  ██║██║███╗██║██║╚██╔╝██║      ─── defensive CTI · Tor-aware ───
  ██████╔╝╚███╔███╔╝██║ ╚═╝ ██║
  ╚═════╝  ╚══╝╚══╝ ╚═╝     ╚═╝
```

> 🛑 **Read [ETHICAL_USE.md](ETHICAL_USE.md) first.** It is the most
> important file in this repository. The licence governs the code;
> that file governs *how the code is used*.

[![Tests](https://img.shields.io/badge/pytest-59%2F59%20passing-brightgreen)](#testing)
[![Bandit](https://img.shields.io/badge/bandit-0%20issues-brightgreen)](results/security_scan.md)
[![pip-audit](https://img.shields.io/badge/pip--audit-0%20vulns-brightgreen)](results/security_scan.md)
[![Semgrep](https://img.shields.io/badge/semgrep-0%20findings-brightgreen)](results/security_scan.md)
[![Eval F1](https://img.shields.io/badge/matcher%20F1-0.9213-brightgreen)](results/README.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Zenodo](https://img.shields.io/badge/zenodo-DOI%20pending-9cf)](.zenodo.json)

`dark-web-monitor-lite` is a defensive cyber-threat-intelligence
tool that watches publicly-indexable onion-service URLs for
matches against an organisational keyword watchlist and dispatches
alerts via Slack, Discord, or generic HTTP webhook.

The tool is intentionally Tor-aware via `stem` + `httpx-socks` but
degrades gracefully when no SOCKS proxy is reachable: every
fetcher returns a typed `FetchResult` so the operator sees coverage
gaps directly in the report.

The **matcher engine** is the only measured component. Live onion
fetches, webhook dispatch, and Tor circuit health are tested with
mocks only — the deliberate choice keeps the eval reproducible
offline.

## Quick start

```bash
git clone https://github.com/thunderstornX/dark-web-monitor-lite.git
cd dark-web-monitor-lite

python -m venv .venv
.venv/bin/pip install -r requirements.txt

# Validate config without making any network call:
.venv/bin/python -m cli.main dry-run \
    --watchlist config/watchlist.yaml \
    --sources config/sources.yaml

# Run a scan (no Tor required for clearnet sources; onion sources
# will report TOR_UNAVAILABLE if no Tor proxy is running):
.venv/bin/python -m cli.main scan \
    --watchlist config/watchlist.yaml \
    --sources config/sources.yaml \
    --output out/scan.json

# Render a crontab line you can paste into your own scheduler:
.venv/bin/python -m cli.main render-cron \
    --watchlist config/watchlist.yaml \
    --sources config/sources.yaml \
    --output /var/log/dwm/scan.json \
    --log /var/log/dwm/scan.log
```

## Architecture

```
                ┌─────────────────────┐
                │ YAML watchlist      │  brands / codenames / iocs
                │ (FICTIONAL default) │  + mandatory _disallowed_categories
                └─────────────────────┘
                            │
                ┌─────────────────────┐
                │ YAML sources        │  public-directory placeholders;
                │ (pre-flight checks) │  requires_auth = false enforced
                └─────────────────────┘
                            │
                ┌─────────────────────┐
                │ Tor SOCKS probe     │  2-second TCP-connect probe;
                │ (graceful fallback) │  failure → TOR_UNAVAILABLE
                └─────────────────────┘
                            │
                ┌─────────────────────┐    ──► JSON report
                │ matcher + fetcher   │
                │ (the measured part) │    ──► Slack / Discord / generic
                └─────────────────────┘        webhooks (all optional)
```

Each fetch returns a typed `FetchResult` with one of:

| Status              | Meaning                                          |
|---------------------|--------------------------------------------------|
| `ok`                | fetched and matcher ran                          |
| `http_error`        | upstream replied 4xx/5xx                         |
| `network_error`     | DNS/connect/transport failure                    |
| `tor_unavailable`   | onion URL + Tor SOCKS proxy unreachable          |
| `timeout`           | exceeded `fetch_timeout_s`                       |
| `skipped_policy`    | source failed a pre-flight policy check          |

## The matcher engine

Two-phase matching per keyword:

1. **Exact** — case-insensitive substring scan. Score is always
   `100.0`.
2. **Fuzzy** (optional, `--no-fuzzy` to disable) — only runs for
   keywords the exact phase did not catch.

The fuzzy scorer uses two strategies:

* **Multi-word keywords**: a sliding-window scan where every keyword
  token must have a near-equivalent body atom; the window's score
  is the **minimum** of per-token best `fuzz.ratio` scores. Aggregating
  with `min` (not `max`) blocks the partial-substring trap that
  simpler rapidfuzz configurations fall into (e.g., `Project
  Aurora` matching `Aurora Borealis`).
* **Single-word keywords**: `fuzz.ratio` against each body atom AND
  against pairs of adjacent atoms joined with no separator — this
  catches CamelCase entries like `AcmeCorp` whose body form is
  space-separated (`Acme Corp`). Tokens under 5 characters are
  never fuzzy-matched.

## Reproducing the eval

```bash
.venv/bin/python eval/run_eval.py
```

55 labelled samples × 10 watchlist keywords = 550 (sample, keyword)
cells. Two configurations measured.

**Latest measured numbers** (2026-05-12):

| Mode         | TP | FP | FN | TN  | Precision | Recall | F1     | Accuracy |
|--------------|---:|---:|---:|----:|----------:|-------:|-------:|---------:|
| exact-only   | 29 |  1 | 13 | 507 | 0.9667    | 0.6905 | 0.8056 | 0.9745   |
| **fuzzy-on** | 41 |  6 |  1 | 502 | **0.8723** | **0.9762** | **0.9213** | **0.9873** |

Fuzzy-on trades 9.4 pp of precision for 28.6 pp of recall; F1
0.806 → **0.921**. See [results/README.md](results/README.md) for
the per-cell residual analysis (7 cells; all defensible — body
negations, plural variants, edge URL tokenisation).

## Testing

```bash
.venv/bin/pytest -q
```

59 tests across the matcher, the Tor probe, the fetcher, the
alerter, the scheduler, the cross-module dataclasses, and the
eval-harness helpers. HTTP is mocked with
[`respx`](https://lundberg.github.io/respx/); no live Tor and no
live webhooks in CI.

| Module                  | Tests |
|-------------------------|------:|
| `matcher.py`            | 22    |
| `alerter.py`            | 10    |
| `fetcher.py`            |  7    |
| `tor_client.py`         |  6    |
| `eval/run_eval.py`      |  6    |
| `findings.py`           |  5    |
| `scheduler.py`          |  3    |
| **Total**               | **59**|

## Security posture

| Gate       | Findings | Suppressions |
|-----------:|:--------:|:------------:|
| Bandit     | 0        | 0            |
| pip-audit  | 0        | 0            |
| Semgrep    | 0        | 0            |

See [results/security_scan.md](results/security_scan.md).

## Compliance baseline

The repository ships three documents intended to be lifted into
the deployer's policy repository:

* **[ETHICAL_USE.md](ETHICAL_USE.md)** — the most important file
  in the repository.
* **[compliance/POLICY_TEMPLATE.md](compliance/POLICY_TEMPLATE.md)** —
  organisational deployment policy template covering authorisation,
  watchlist governance, source list governance, operational guard-
  rails, incident handling, data retention, audit, and sunset.
* **[compliance/LEGAL_REVIEW.md](compliance/LEGAL_REVIEW.md)** — a
  four-jurisdiction summary (United States, United Kingdom,
  European Union, Pakistan) of the statutes that constrain passive
  monitoring. **This is not legal advice.** It is designed to
  surface the questions a real legal review would have to answer.

## What this tool does *not* do

* It does **not** create accounts on illicit services.
* It does **not** purchase, attempt to purchase, or solicit illicit
  goods, services, or data.
* It does **not** scrape paid, breach-broker, or non-publicly-
  indexable services. ETHICAL_USE.md defines "publicly accessible"
  strictly: indexed by a public Tor search engine, no account, no
  payment, no invitation, no per-user authorisation.
* It does **not** retain captured content. Body content is hashed
  for dedup and discarded by default.
* It does **not** target individual people.

## Citing

If you use this software in academic work, please cite the
[CITATION.cff](CITATION.cff) record. The companion
[IEEE paper](paper/paper.tex) describes the design and reports
live measurements.

## License

MIT. See [LICENSE](LICENSE). The licence governs the code;
[ETHICAL_USE.md](ETHICAL_USE.md) governs how the code is used.
