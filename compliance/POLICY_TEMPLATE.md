# Organisational deployment policy template

> Copy this file into your organisation's policy repository, fill in
> every `<bracketed placeholder>`, route the result through your
> legal / compliance function, and have it approved *before* you
> deploy `dark-web-monitor-lite`. Deploying without an approved
> policy is itself a finding — most regulators treat it as
> uncontrolled use of investigatory tooling.

---

## 1. Purpose and scope

This policy governs the operation of `dark-web-monitor-lite` (the
"Tool") within `<Organisation Name>` ("the Organisation").

The Tool is operated solely for **defensive cyber-threat
intelligence** purposes, specifically the early detection of
publicly-indexable mentions of:

- the Organisation's registered names, trading names, and brand
  identifiers;
- the Organisation's customer-facing domain names;
- internal product codenames flagged for monitoring by the CTI
  team;
- IOC strings produced by the Organisation's incident response
  function.

The Tool **must not** be operated for any other purpose, including
but not limited to: research about other organisations, journalism,
personal interest, surveillance of individuals, or competitive
intelligence about other companies.

## 2. Authorisation

Operating the Tool in the Organisation's name requires written
authorisation from **both** of the following functions, signed
within the last 12 months:

| Function                  | Approver role                          |
|---------------------------|----------------------------------------|
| Legal / Compliance        | `<General Counsel or designate>`       |
| Information Security      | `<CISO or designate>`                  |

Authorisation must name the specific operator(s), the watchlist
scope, and the maximum scan cadence. Authorisation lapses
automatically after 12 months unless renewed.

## 3. Watchlist governance

* Watchlist entries are added only by named CTI team members.
* Each entry has a documented owner and a justification.
* Personal names of natural persons are **not** valid watchlist
  entries except where the named person is a director or officer
  whose monitoring is mandated by a regulatory or insurance
  requirement.
* Watchlists are stored encrypted at rest and never committed to
  any version-control system, public or private.
* The watchlist file's `_disallowed_categories` block (in the YAML
  schema) is **mandatory**; the Tool refuses to load watchlists
  that omit it.

## 4. Source list governance

* Source URLs are added only after a documented review confirms
  the source meets the four-part "publicly accessible" definition
  in `ETHICAL_USE.md` §"What 'publicly accessible' actually means".
* Sources whose status changes (e.g., previously-public source
  introduces a paywall or registration) must be removed from the
  list within **7 calendar days** of the change being observed.
* Adding a source whose content is criminal in the operator's
  jurisdiction (e.g., child-sexual-abuse material indexes) is
  **prohibited** even if the source is technically "public". This
  is a hard rule, not a guideline.

## 5. Operational guard-rails

* The Tool runs from a dedicated, hardened host. The host must
  not be used for any other production workload.
* Tor connectivity is provided by a separate Tor daemon process,
  ideally in a separate container, with no inbound exposure.
* Webhook destinations are restricted to internal CTI channels.
  Public Slack channels, personal accounts, and SMS gateways are
  **not** valid destinations.
* The Tool's telemetry (scan counts, error rates) is shipped to
  the Organisation's central logging system. Telemetry that
  contains content snippets is redacted before shipping.
* Scan cadence is rate-limited at the Tool level, not at the
  source level — this protects sources from DoS-by-monitor.

## 6. Incident handling

If the Tool produces a match that meets any of the following
conditions, the operator must escalate to the named Incident
Commander within `<X>` business hours:

| Condition                                              | Severity   |
|--------------------------------------------------------|------------|
| Match against a customer-data IOC                      | Critical   |
| Match against a credential string (account/password)   | Critical   |
| Match against an internal codename never disclosed     | High       |
| Brand mention with apparent extortion language         | High       |
| Generic brand mention without further context          | Informational |

Incident handling itself is governed by the Organisation's
existing IR runbook; the Tool only generates the lead.

## 7. Data retention

* Match metadata (timestamp, source URL, matched keyword,
  rapidfuzz score) is retained for **`<N>` calendar days**.
* Body content is hashed for dedup and discarded immediately;
  the dedup hash is retained for the same `<N>` days.
* Operator-authored notes attached to a match are retained per
  the Organisation's standard incident-record retention policy.

## 8. Audit

* The Tool's full operational log (every scan, every fetch
  outcome, every alert dispatch) is retained for at least
  **365 days** in tamper-evident storage.
* The CTI team conducts a quarterly self-audit of the watchlist,
  source list, and operator authorisations. The audit record is
  produced for the Compliance function on request.

## 9. Sunset

This policy expires `<date 12 months from approval>`. Renewal
requires re-execution of clauses 2 and 8.

---

*Template version 1.0. Maintained alongside the
`dark-web-monitor-lite` repository at
<https://github.com/thunderstornX/dark-web-monitor-lite>. The
template itself is MIT-licensed; the Organisation's filled-in
copy carries whatever classification the Organisation assigns.*
