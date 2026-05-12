# Jurisdictional legal review (informational)

> **This is not legal advice.** It is a four-jurisdiction summary
> intended to surface the questions a real legal review would have
> to answer. An organisation considering operating
> `dark-web-monitor-lite` must obtain advice from counsel
> qualified in the relevant jurisdiction before deployment. The
> summaries below are accurate as of the date of writing
> (2026-05-06) but are deliberately conservative; readers are
> encouraged to read the cited primary sources.

The four jurisdictions covered are the United States, the United
Kingdom, the European Union (taken at the directive level, not
the per-member-state implementation level), and Pakistan. They
are chosen because the maintainer has a working understanding of
each; they are not the only jurisdictions a deployer should
consider.

---

## United States

### Headline position

Connecting to the Tor network and reading publicly-indexable
content from onion services is **not, in itself, illegal** in the
United States. The Tor Project is a U.S. nonprofit and onion
services are widely used for entirely lawful purposes. The
relevant constraints lie elsewhere.

### Statutes that constrain behaviour

* **18 U.S.C. § 1030 (Computer Fraud and Abuse Act, CFAA).** The
  CFAA prohibits accessing a computer "without authorisation" or
  in excess of authorisation. The post-*Van Buren v. United
  States* (2021) reading is narrower than older case law: a
  user who is allowed to log in but exceeds the *purpose* of the
  authorisation is no longer per se in CFAA territory. Even so,
  any source that requires account creation falls outside the
  bounds the Tool itself enforces.
* **17 U.S.C. § 506 (criminal copyright infringement).**
  Mass-downloading copyrighted material from infringing sources
  is a separate liability surface from the CFAA question above.
* **State-level privacy statutes.** Several states (e.g., CA,
  NY, IL) regulate the storage of biometric or personal data
  even when collected from a public source. The Tool's
  hash-and-discard default is intended to keep operators well
  clear of these.

### Practical posture for a U.S. deployer

* Scan only sources that meet the four-part "publicly
  accessible" test in `ETHICAL_USE.md`.
* Have your General Counsel sign off on the watchlist before
  the first scan.
* Do not retain bodies. Hash-and-discard is the default for
  exactly this reason.

---

## United Kingdom

### Headline position

The same general principle applies: connecting to Tor and reading
publicly-indexable content is not in itself unlawful. Liability
in the UK comes from the *Computer Misuse Act 1990* (CMA) and a
small number of content-specific offences.

### Statutes that constrain behaviour

* **Computer Misuse Act 1990, s.1.** "Unauthorised access" to
  computer material is the headline offence. As in the U.S.,
  this is a question of authorisation, not of network. Sources
  that require an account or that the operator has been told to
  stay away from move out of bounds.
* **Investigatory Powers Act 2016.** Sections governing
  *targeted equipment interference* apply to public bodies,
  not most private companies, but the principle that
  surveillance of individuals requires proportionality is
  read across by regulators (ICO) into private-sector activity.
* **Data Protection Act 2018 / UK GDPR.** Article 6 lawful
  bases apply to any personal data the Tool processes incidental
  to monitoring. Recital 47 ("legitimate interests") is the
  most likely basis for defensive monitoring of one's own
  identifiers, but the legitimate-interests assessment must be
  documented before deployment.

### Practical posture for a UK deployer

* Run a Data Protection Impact Assessment before first scan.
* Do not include personal-identifier watchlist entries unless
  the named person is an officer of the company *and* the
  legitimate-interests assessment specifically covers them.
* Retain the operational log for ICO-evidence purposes.

---

## European Union

### Headline position

EU law sets the *floor* for member-state implementations.
Practitioners must consult the per-member-state implementation
of the directives below; the EU-level summary here is
deliberately not deployment-ready.

### Instruments that constrain behaviour

* **Directive 2013/40/EU on attacks against information
  systems.** Article 3 (illegal access) is the EU analogue of
  the CFAA / CMA. Member-state implementations vary.
* **Regulation (EU) 2016/679 (GDPR).** Articles 5 and 6 govern
  any incidental processing of personal data; Article 9 covers
  special-category data, including political opinion, which is
  highly relevant to dark-web content. The Tool's
  hash-and-discard default is specifically intended to keep the
  default-deployment posture under Article 5(1)(c) (data
  minimisation).
* **NIS2 Directive (Directive (EU) 2022/2555).** Operators of
  essential and important entities have notification
  obligations that may be triggered by Tool findings. The
  policy template assumes this; deployers must confirm
  applicability in their own implementation.

### Practical posture for an EU deployer

* Do a Data Protection Impact Assessment per Article 35.
* Map any planned monitoring to a specific Article 6 lawful
  basis and document the mapping.
* Obtain works-council / employee-representative input where
  the Tool's deployment touches on workforce-monitoring
  considerations.

---

## Pakistan

### Headline position

Pakistan's electronic-crimes statute is the *Prevention of
Electronic Crimes Act 2016 (PECA)*. The PECA's headline offences
include unauthorised access (s.3), unauthorised data
acquisition (s.4), and "cyber terrorism" (s.10). The PECA also
contains provisions (s.37 in particular) that operators outside
state agencies should treat with care.

### Statutes that constrain behaviour

* **PECA 2016, s.3-4.** Unauthorised access and data
  acquisition. The same authorisation analysis applies as in
  the U.S. and U.K.
* **PECA 2016, s.10.** "Cyber terrorism" is broadly defined and
  defensive deployers should ensure their watchlist and scope
  are documented to make clear the Tool is operating against
  the operator's own identifiers.
* **PECA 2016, s.37 (unlawful online content).** Removal /
  blocking provisions apply to content disseminators rather
  than monitors, but the relationship between the Tool's output
  (a finding) and downstream removal requests is a question
  worth addressing in the policy.

### Practical posture for a Pakistan-based deployer

* Have the Tool's deployment notified to the Federal
  Investigation Agency (FIA) cyber-crime wing before first
  operational scan, where the deployer is a regulated
  financial-sector or critical-infrastructure operator.
* Keep the operational log retained per PECA evidentiary
  requirements (typically 12 months minimum, deployer's
  counsel to confirm).
* Do not act on findings outside the Organisation's authorised
  channel; route everything via the FIA where the finding
  involves a credible imminent harm.

---

## What this review is *not*

* It is not jurisdiction-specific advice.
* It is not exhaustive even within the four jurisdictions
  covered.
* It is not a substitute for legal counsel.
* It is not stable: the cited statutes are amended periodically
  and the case law moves. The deployer's compliance function is
  responsible for tracking changes.

## Primary sources cited

* United States: 18 U.S.C. § 1030; *Van Buren v. United States*,
  593 U.S. ___ (2021).
* United Kingdom: Computer Misuse Act 1990; Investigatory Powers
  Act 2016; Data Protection Act 2018.
* European Union: Directive 2013/40/EU; Regulation (EU)
  2016/679 (GDPR); Directive (EU) 2022/2555 (NIS2).
* Pakistan: Prevention of Electronic Crimes Act 2016.

*Template version 1.0. Provided as a starting point; deployers
should engage qualified counsel for actual advice.*
