"""Tests for the matcher engine (the measured component)."""
from __future__ import annotations

import pytest

from monitor.findings import MatchKind
from monitor.matcher import (
    _DISALLOWED_KEY,
    _REQUIRED_DISALLOWED,
    Watchlist,
    load_watchlist,
    scan_bodies,
    scan_body,
)


_DISALLOWED_BLOCK = sorted(_REQUIRED_DISALLOWED)


# ---------------------------------------------------------------------------
# Watchlist loader
# ---------------------------------------------------------------------------

def test_load_watchlist_happy_path():
    wl = load_watchlist({
        "brands": ["AcmeCorp"],
        "_disallowed_categories": _DISALLOWED_BLOCK,
    })
    assert wl.keywords == ("AcmeCorp",)


def test_load_watchlist_rejects_missing_disallowed_block():
    with pytest.raises(ValueError, match="_disallowed_categories"):
        load_watchlist({"brands": ["X"]})


def test_load_watchlist_rejects_partial_disallowed_block():
    with pytest.raises(ValueError, match="missing categories"):
        load_watchlist({
            "brands": ["X"],
            "_disallowed_categories": ["personal_names"],
        })


def test_load_watchlist_deduplicates_case_insensitively():
    wl = load_watchlist({
        "brands": ["AcmeCorp", "acmecorp", "ACMECORP"],
        "_disallowed_categories": _DISALLOWED_BLOCK,
    })
    assert wl.keywords == ("AcmeCorp",)


def test_load_watchlist_rejects_empty_after_filtering():
    with pytest.raises(ValueError, match="no keywords"):
        load_watchlist({"_disallowed_categories": _DISALLOWED_BLOCK})


def test_load_watchlist_rejects_non_list_value():
    with pytest.raises(ValueError, match="list of strings"):
        load_watchlist({
            "brands": "not-a-list",
            "_disallowed_categories": _DISALLOWED_BLOCK,
        })


def test_load_watchlist_rejects_non_string_entry():
    with pytest.raises(ValueError, match="non-string"):
        load_watchlist({
            "brands": ["AcmeCorp", 42],
            "_disallowed_categories": _DISALLOWED_BLOCK,
        })


def test_load_watchlist_rejects_non_mapping_root():
    with pytest.raises(ValueError, match="mapping"):
        load_watchlist(["just a list"])


# ---------------------------------------------------------------------------
# Exact matcher
# ---------------------------------------------------------------------------

def test_exact_match_case_insensitive(watchlist):
    out = scan_body("ACMECORP breach disclosed.", watchlist,
                     source_url="t", fuzzy=False)
    kinds = [m.kind for m in out]
    keywords = [m.keyword for m in out]
    assert MatchKind.EXACT in kinds
    assert "AcmeCorp" in keywords


def test_exact_match_multiple_occurrences_yield_multiple_matches(watchlist):
    out = scan_body("AcmeCorp and AcmeCorp again", watchlist,
                     source_url="t", fuzzy=False)
    acme_matches = [m for m in out if m.keyword == "AcmeCorp"]
    assert len(acme_matches) == 2


def test_exact_match_returns_zero_for_clean_body(watchlist):
    out = scan_body("Nothing of interest here.", watchlist,
                     source_url="t", fuzzy=False)
    assert out == []


def test_exact_match_score_is_100(watchlist):
    out = scan_body("AcmeCorp mention.", watchlist,
                     source_url="t", fuzzy=False)
    assert any(m.kind == MatchKind.EXACT and m.score == 100.0
                for m in out)


# ---------------------------------------------------------------------------
# Fuzzy matcher
# ---------------------------------------------------------------------------

def test_fuzzy_catches_camelcase_compound_written_with_space(watchlist):
    out = scan_body("Acme Corp incident verified.", watchlist,
                     source_url="t", fuzzy=True, threshold=85)
    assert any(m.keyword == "AcmeCorp" and m.kind == MatchKind.FUZZY
                for m in out)


def test_fuzzy_catches_typo_in_codename(watchlist):
    out = scan_body("Project Aurorra leaked.", watchlist,
                     source_url="t", fuzzy=True, threshold=85)
    assert any(m.keyword == "Project Aurora" for m in out)


def test_fuzzy_skips_short_single_word_keywords(watchlist):
    """The watchlist contains 'FCo' (3 chars). It must never fuzzy-match —
    only exact."""
    out = scan_body("FCO is a UK government body.", watchlist,
                     source_url="t", fuzzy=True, threshold=85)
    # Should fire on FCo because exact match is case-insensitive,
    # but we want to be sure no other 3-letter substring of the body
    # triggers a fuzzy match.
    fuzzy_for_fco = [m for m in out
                      if m.keyword == "FCo" and m.kind == MatchKind.FUZZY]
    assert fuzzy_for_fco == []


def test_fuzzy_rejects_unrelated_substring(watchlist):
    """The 'Aurora Borealis' case: should not match 'Project Aurora'."""
    out = scan_body("Aurora Borealis and Northern Lights.", watchlist,
                     source_url="t", fuzzy=True, threshold=85)
    assert all(m.keyword != "Project Aurora" for m in out)


def test_fuzzy_does_not_fire_on_keyword_already_exact_matched(watchlist):
    """Exact phase fires first; fuzzy phase MUST skip that keyword."""
    out = scan_body("AcmeCorp leak.", watchlist,
                     source_url="t", fuzzy=True, threshold=85)
    acme_matches = [m for m in out if m.keyword == "AcmeCorp"]
    assert len(acme_matches) == 1
    assert acme_matches[0].kind == MatchKind.EXACT


def test_fuzzy_multi_word_requires_both_tokens_present(watchlist):
    """'Aurora-Zenith' must require both 'Aurora' AND 'Zenith' tokens —
    'just Aurora' is not enough."""
    out = scan_body("Just Aurora was named in the dump.", watchlist,
                     source_url="t", fuzzy=True, threshold=85)
    assert all(m.keyword != "Aurora-Zenith" for m in out)


def test_fuzzy_threshold_is_respected(watchlist):
    """A high-threshold scan should reject borderline matches that a
    lower-threshold scan would accept."""
    body = "Project Aurorra (sic) leaked."
    lo = scan_body(body, watchlist, source_url="t",
                    fuzzy=True, threshold=85)
    hi = scan_body(body, watchlist, source_url="t",
                    fuzzy=True, threshold=99)
    assert any(m.keyword == "Project Aurora" for m in lo)
    assert all(m.keyword != "Project Aurora" for m in hi)


# ---------------------------------------------------------------------------
# scan_bodies (multi-source)
# ---------------------------------------------------------------------------

def test_scan_bodies_aggregates(watchlist):
    bodies = {
        "src-1": "AcmeCorp leak.",
        "src-2": "Project Aurorra typo'd here.",
        "src-3": "Unrelated post.",
    }
    out = scan_bodies(bodies, watchlist, fuzzy=True, threshold=85)
    by_source = {m.source_url for m in out}
    assert "src-1" in by_source
    assert "src-2" in by_source
    assert "src-3" not in by_source


def test_match_span_truncated(watchlist):
    body = "X " * 100 + "AcmeCorp here"
    out = scan_body(body, watchlist, source_url="t",
                     fuzzy=False)
    for m in out:
        assert len(m.span) <= 80


def test_exact_match_records_real_substring(watchlist):
    """Exact match span should be the actual matched substring, not
    a reformatted version."""
    out = scan_body("breach by acMeCorP today", watchlist,
                     source_url="t", fuzzy=False)
    assert any(m.span.lower() == "acmecorp" for m in out)
