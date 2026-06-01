# Ethical use

> **This file is the most important file in the repository.** Read it
> before you read the README. Read it again before you point the tool
> at any non-fictitious target. The licence governs the code; this
> file governs *how the code is used*.

`dark-web-monitor-lite` is a defensive cyber-threat-intelligence
tool. Its job is to help an internal CTI team detect when their
*own organisation's* identifiers appear on publicly-indexable
onion-service pages so the team can route the finding to the
appropriate incident-response or law-enforcement channel. It is
not, and must not become, a research crawler for illicit
marketplaces, a journalism aid, a doxxing tool, or a personal
curiosity project.

## What the tool does

* Reads a watchlist of keywords (org names, internal identifiers,
  product codenames, IOC strings) from a YAML file.
* Reads a list of publicly-known onion-service URLs from a YAML
  file. The shipped sample only references public directory and
  search services (e.g., the Ahmia search index) — see
  `config/sources.yaml`.
* Optionally connects to a local Tor SOCKS5 proxy (default
  `127.0.0.1:9050`) and fetches each source. If no Tor proxy is
  reachable, the fetcher returns
  `FetchStatus.TOR_UNAVAILABLE` and the report shows the
  coverage gap rather than silently dropping the source.
* Runs each fetched body through a deterministic exact-match
  scanner and an optional fuzzy matcher
  (rapidfuzz, default threshold 85).
* Dispatches alerts via webhook (Slack, Discord, or generic HTTP
  POST) for each match.

## What the tool does *not* do, ever

* It does **not** create accounts on illicit services. Many onion
  marketplaces require account creation to view content; we treat
  any source that requires account creation as out of scope, full
  stop.
* It does **not** purchase, attempt to purchase, or solicit
  illicit goods, services, or data. There is no "test purchase"
  feature and there will not be one.
* It does **not** scrape paid, breach-broker, or non-publicly-
  indexable services. Public means *publicly indexable, with no
  authentication, no payment, no invitation*.
* It does **not** retain captured content. The report contains
  matched *keywords* and source URLs. Body content is hashed for
  dedup and discarded; raw bodies are not written to disk by
  default. (`captures/` is in `.gitignore` and operators who choose
  to retain bodies for incident-response reasons must take that
  decision deliberately.)
* It does **not** target individual people. The watchlist is for
  organisational identifiers. Watchlist entries that look like
  personal names will produce a noisy report; this is by design.
* It does **not** target lawyers, journalists, activists, or
  political opposition. The watchlist YAML's
  `_disallowed_categories` block makes this explicit and the
  parser refuses to load watchlists that contain those categories.

## What "publicly accessible" actually means here

Inside the dark web research community there is genuine
disagreement about where "public" ends. We adopt the strict
definition:

  A resource is *publicly accessible* if and only if **every** of the
  following are true:

  1. It is indexed by a public Tor search engine (e.g., Ahmia)
     **or** it is linked from a publicly-published research /
     directory page maintained by a recognised non-profit.
  2. Loading the resource requires no account, no payment, no
     invitation, no captcha-bypass.
  3. The content is not behind a per-user authorisation gate at
     any layer (HTTP basic, OAuth, marketplace login).
  4. The site does not require the user to assert criminal
     intent (e.g., "click here if you are a buyer").

Sources that fail any of these are out of scope and the
`config/sources.yaml` schema documents this.

## Authorised use only

By using this software you affirm that:

1. You have authority to monitor the keywords on your watchlist —
   they are your own organisation's identifiers, or you are
   acting under a written engagement letter from the owning
   organisation.
2. You are authorised by your organisation's legal or compliance
   function to operate dark-web monitoring tooling. In several
   jurisdictions (see `compliance/LEGAL_REVIEW.md`) merely
   *connecting* to the Tor network from a corporate network is a
   policy decision, never a personal one.
3. You will not use the tool for journalism, dox research,
   personal curiosity, or surveillance of individuals.
4. You will route any finding involving evidence of an active
   crime through your organisation's incident-response or
   legal channel — not directly to any third party, not to social
   media, not to a public bug tracker.
5. You will not use the tool's match results to *engage with* the
   source. The tool is for detection only; engaging (replying,
   commenting, registering) requires a separate authorised
   channel that is out of scope of this software.
6. If you redistribute the tool, you keep this file and carry the
   same restrictions through.

## Operating-environment hardening

The tool's threat surface is the operator's machine, not the
target. Recommendations:

* Run the tool inside a dedicated VM or container. The shipped
  `docker-compose.yml` (when added in a future release) will
  default to a non-privileged user inside the container.
* Pin the Tor daemon to a separate process / container. Never give
  the tool the Tor control port unless you understand the
  implications.
* Send webhook alerts to a dedicated channel that your CTI team
  monitors. Do not route them to a public Slack channel.
* Keep your watchlist out of the public repository. The YAML
  schema's `_storage_recommendation` field explicitly says
  "encrypted at rest, never committed".

## Framework attributions

* The tool's threat model is consistent with NIST SP 800-150
  (Guide to Cyber Threat Information Sharing, October 2016) which
  treats CTI consumption as an organisational, not individual,
  activity.
* The Ahmia indexing service is © Ahmia.fi project; using its
  index URL in `config/sources.yaml` does not imply endorsement
  by Ahmia of this tool.
* The Tor Project is © The Tor Project, Inc.; routing fetches through
  a Tor SOCKS proxy does not imply Tor Project endorsement.

## Reporting misuse

If you discover this software being used in a way that violates
these terms, please open an issue on the repository and tag it
`ethical-use-violation`. We will collaborate with the affected
party to constrain the deployment.

This software is provided as-is under the MIT license. The licence
does not override the ethical and legal expectations above; the two
stand together.
