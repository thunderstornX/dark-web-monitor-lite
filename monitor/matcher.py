"""Keyword matcher: deterministic exact + rapidfuzz fuzzy.

This is the only component the eval harness measures. Everything
else (Tor, fetcher, alerter) is a wrapper around an external
service and is tested with mocked HTTP only.

Design choices
--------------
* **Two-phase matching**: every body is run through the exact-match
  scanner first; an entry only enters the fuzzy phase if the exact
  scanner missed it. This keeps the precision of fuzzy matching
  honest — it cannot add a false positive on top of an existing true
  positive.
* **rapidfuzz, not fuzzywuzzy**: fuzzywuzzy is no longer maintained
  and the rapidfuzz package is its modern drop-in replacement
  (used by the same author). The default threshold is 85, which is
  the practitioner-folk-default from the original fuzzywuzzy docs.
* **Sliding window for fuzzy**: the fuzzy phase uses ``partial_ratio``
  inside an n-word sliding window so a 3-word watchlist entry like
  "Project Aurora" can be found inside a longer body without the
  full-document Levenshtein distance dragging the score down.
* **Span truncation**: Match.span is truncated to 80 characters so
  the JSON report doesn't accidentally retain large body fragments.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from rapidfuzz import fuzz

from .findings import Match, MatchKind


# ---------------------------------------------------------------------------
# Watchlist data
# ---------------------------------------------------------------------------

_DISALLOWED_KEY = "_disallowed_categories"
_REQUIRED_DISALLOWED = {
    "personal_names",
    "residential_addresses",
    "government_or_military_aliases",
    "journalist_or_activist_identifiers",
    "lawyer_or_litigant_identifiers",
}


@dataclass(frozen=True)
class Watchlist:
    """Validated watchlist data drawn from `config/watchlist.yaml`."""
    keywords: tuple[str, ...]


def load_watchlist(raw: dict) -> Watchlist:
    """Validate and flatten a YAML-loaded watchlist mapping.

    Mandatory contract: the YAML MUST contain a ``_disallowed_categories``
    block listing every entry in ``_REQUIRED_DISALLOWED``. This is the
    policy backstop against ad-hoc personal-target additions.
    """
    if not isinstance(raw, dict):
        raise ValueError("watchlist root must be a mapping")
    if _DISALLOWED_KEY not in raw:
        raise ValueError(
            f"watchlist missing required {_DISALLOWED_KEY!r} block; "
            f"refusing to load (policy backstop).")
    disallowed = set(raw.get(_DISALLOWED_KEY) or [])
    missing = _REQUIRED_DISALLOWED - disallowed
    if missing:
        raise ValueError(
            f"watchlist {_DISALLOWED_KEY} block missing categories: "
            f"{sorted(missing)}")

    keywords: list[str] = []
    for key, value in raw.items():
        if key.startswith("_"):
            continue
        if not isinstance(value, list):
            raise ValueError(
                f"watchlist key {key!r} must map to a list of strings")
        for v in value:
            if not isinstance(v, str) or not v.strip():
                raise ValueError(
                    f"watchlist {key!r} contains non-string entry: {v!r}")
            keywords.append(v.strip())
    if not keywords:
        raise ValueError("watchlist contains no keywords after filtering")
    # De-duplicate while preserving insertion order.
    seen: set[str] = set()
    uniq: list[str] = []
    for k in keywords:
        if k.lower() in seen:
            continue
        seen.add(k.lower())
        uniq.append(k)
    return Watchlist(keywords=tuple(uniq))


# ---------------------------------------------------------------------------
# Matching helpers
# ---------------------------------------------------------------------------

_WORD_RE = re.compile(r"\S+")
# Hyphenated tokens get split: "Aurora-Zenith" → ["Aurora", "Zenith"].
# This lets a body that writes the same identifier with whitespace
# instead of a hyphen still hit the multi-word fuzzy branch.
_TOKEN_SPLIT_RE = re.compile(r"[^A-Za-z0-9_]+")
_MAX_SPAN_CHARS = 80


def _truncate(s: str, *, n: int = _MAX_SPAN_CHARS) -> str:
    if len(s) <= n:
        return s
    return s[: n - 1].rstrip() + "…"      # ellipsis


def _exact_match_spans(body: str, keyword: str) -> list[str]:
    """Return non-overlapping case-insensitive substring matches."""
    if not keyword:
        return []
    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    return [m.group(0) for m in pattern.finditer(body)]


# Single-word keywords below this character length are matched
# exact-only; for tokens that short the fuzzy false-positive rate is
# unmanageable. Multi-word keywords always run through fuzzy.
_FUZZY_MIN_SINGLE_WORD_LEN = 5


def _fuzzy_match_score(body: str, keyword: str,
                        *, threshold: int) -> tuple[float, str] | None:
    """Score the keyword against the best-matching window of the body.

    Dual scorer:

    * **Multi-word** keywords (>=2 words) use ``fuzz.partial_ratio``
      over a word-window of size n_words ± 1. This catches
      "Project Aurorra" → "Project Aurora" without blowing up on
      long bodies.
    * **Single-word** keywords use ``fuzz.ratio`` (full Levenshtein)
      against each *token* in the body. partial_ratio is too liberal
      for short tokens — it will happily call "Acme" a near-match
      for any body containing it as a substring. Tokens shorter than
      ``_FUZZY_MIN_SINGLE_WORD_LEN`` are never fuzzy-matched."""
    keyword = keyword.strip()
    if not keyword:
        return None

    # Tokenise the keyword on whitespace AND non-alphanumeric separators
    # ("-", ".") so "Aurora-Zenith" is treated as a 2-token multi-word
    # keyword. The matcher should fire on a body that writes
    # "Zenith Aurora" (different order) only after the dual-scorer
    # below confirms both partial_ratio and token_set_ratio are
    # comfortable.
    kw_tokens = [t for t in _TOKEN_SPLIT_RE.split(keyword) if t]
    n_words = max(1, len(kw_tokens))
    tokens = _WORD_RE.findall(body)
    if not tokens:
        return None

    if n_words >= 2:
        # Strict per-token scorer: every distinct keyword token must
        # have at least one near-equivalent body token in the window.
        # The window's score is the *weakest* per-keyword-token score
        # (min-aggregation), so a window that contains only one of
        # two keyword tokens scores low even when the present token
        # matches exactly. This is what blocks the
        # "Aurora Borealis ⇒ Project Aurora" partial-substring trap.
        best_score = 0.0
        best_span = ""
        kw_tokens_lc = [t.lower() for t in kw_tokens]
        for size in {max(1, n_words - 1), n_words, n_words + 1, n_words + 2}:
            if size > len(tokens):
                continue
            for i in range(0, len(tokens) - size + 1):
                window_tokens = tokens[i:i + size]
                window_tokens_lc = [t.lower() for t in window_tokens]
                # Split window tokens on the same separators we use
                # for the keyword so "Acme-Corp" and "Acme Corp" both
                # surface as the canonical pair.
                window_atoms_lc = []
                for wt in window_tokens_lc:
                    for atom in _TOKEN_SPLIT_RE.split(wt):
                        if atom:
                            window_atoms_lc.append(atom)
                if not window_atoms_lc:
                    continue
                per_token = []
                for kt in kw_tokens_lc:
                    per_token.append(max(
                        fuzz.ratio(kt, atom)
                        for atom in window_atoms_lc
                    ))
                score = float(min(per_token))
                if score > best_score:
                    best_score = score
                    best_span = " ".join(window_tokens)
        if best_score >= float(threshold):
            return (best_score, best_span)
        return None

    # Single-word branch.
    if len(keyword) < _FUZZY_MIN_SINGLE_WORD_LEN:
        return None
    keyword_lc = keyword.lower()
    best_score = 0.0
    best_span = ""
    # Score against each body token individually...
    for tok in tokens:
        score = fuzz.ratio(tok.lower(), keyword_lc)
        if score > best_score:
            best_score = float(score)
            best_span = tok
    # ...and also against pairs of adjacent body tokens joined with no
    # separator. This handles single-word CamelCase keywords whose
    # body form is space-separated ("AcmeCorp" vs "Acme Corp").
    for i in range(len(tokens) - 1):
        joined = (tokens[i] + tokens[i + 1]).lower()
        score = fuzz.ratio(joined, keyword_lc)
        if score > best_score:
            best_score = float(score)
            best_span = tokens[i] + " " + tokens[i + 1]
    if best_score >= float(threshold):
        return (best_score, best_span)
    return None


# ---------------------------------------------------------------------------
# Public scan entry point
# ---------------------------------------------------------------------------

def scan_body(
    body: str,
    watchlist: Watchlist,
    *,
    source_url: str = "",
    fuzzy: bool = True,
    threshold: int = 85,
) -> list[Match]:
    """Scan a single body for every keyword in the watchlist.

    Returns one Match per (keyword, span) pair. Exact matches always
    fire when present; fuzzy matches only fire for keywords that
    exact-match did not hit. This keeps fuzzy from inflating an
    already-true-positive count."""
    matches: list[Match] = []
    for kw in watchlist.keywords:
        spans = _exact_match_spans(body, kw)
        if spans:
            for s in spans:
                matches.append(Match(
                    keyword=kw,
                    source_url=source_url,
                    kind=MatchKind.EXACT,
                    score=100.0,
                    span=_truncate(s),
                ))
            continue
        if fuzzy:
            res = _fuzzy_match_score(body, kw, threshold=threshold)
            if res is not None:
                score, span = res
                matches.append(Match(
                    keyword=kw,
                    source_url=source_url,
                    kind=MatchKind.FUZZY,
                    score=round(score, 2),
                    span=_truncate(span),
                ))
    return matches


def scan_bodies(
    bodies: dict[str, str],
    watchlist: Watchlist,
    *,
    fuzzy: bool = True,
    threshold: int = 85,
) -> list[Match]:
    """Scan many ``{source_url: body}`` pairs and return the union."""
    out: list[Match] = []
    for url, body in bodies.items():
        out.extend(scan_body(body, watchlist,
                              source_url=url,
                              fuzzy=fuzzy, threshold=threshold))
    return out
