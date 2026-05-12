"""Tests for the eval harness's confusion-matrix logic + corpus invariants."""
from __future__ import annotations

import json
from pathlib import Path

from eval.run_eval import _confusion
from monitor.matcher import Watchlist, load_watchlist


_REPO = Path(__file__).resolve().parent.parent
_CORPUS = _REPO / "eval" / "labelled_corpus.json"
_DISALLOWED = [
    "personal_names",
    "residential_addresses",
    "government_or_military_aliases",
    "journalist_or_activist_identifiers",
    "lawyer_or_litigant_identifiers",
]


def _load_corpus_watchlist() -> tuple[list[dict], Watchlist]:
    raw = json.loads(_CORPUS.read_text())
    wl = load_watchlist({
        "iocs": raw["watchlist"],
        "_disallowed_categories": _DISALLOWED,
    })
    return raw["samples"], wl


def test_corpus_loads_55_samples():
    samples, _ = _load_corpus_watchlist()
    assert len(samples) == 55


def test_corpus_watchlist_has_10_keywords():
    _, wl = _load_corpus_watchlist()
    assert len(wl.keywords) == 10


def test_corpus_has_mix_of_classes():
    samples, _ = _load_corpus_watchlist()
    ids = [s["id"] for s in samples]
    assert any(i.startswith("exact-")  for i in ids)
    assert any(i.startswith("fuzzy-")  for i in ids)
    assert any(i.startswith("noise-")  for i in ids)
    assert any(i.startswith("tricky-") for i in ids)
    assert any(i.startswith("long-")   for i in ids)


def test_confusion_exact_only_perfect_for_obvious_exact_match():
    """A pre-curated mini-corpus where every expected is an exact
    substring should produce 0 FP / 0 FN in exact-only mode."""
    wl = load_watchlist({
        "iocs": ["AcmeCorp", "ExampleInc"],
        "_disallowed_categories": _DISALLOWED,
    })
    samples = [
        {"id": "a", "body": "AcmeCorp leak", "expected": ["AcmeCorp"]},
        {"id": "b", "body": "ExampleInc dump", "expected": ["ExampleInc"]},
        {"id": "c", "body": "nothing", "expected": []},
    ]
    res = _confusion(samples, wl, fuzzy=False, threshold=85)
    assert res["fp"] == 0
    assert res["fn"] == 0
    assert res["precision"] == 1.0
    assert res["recall"] == 1.0


def test_confusion_recall_improves_with_fuzzy_on():
    samples, wl = _load_corpus_watchlist()
    exact = _confusion(samples, wl, fuzzy=False, threshold=85)
    fuzzy = _confusion(samples, wl, fuzzy=True, threshold=85)
    assert fuzzy["recall"] >= exact["recall"]
    assert fuzzy["tp"] >= exact["tp"]


def test_confusion_universe_matches_grid():
    samples, wl = _load_corpus_watchlist()
    res = _confusion(samples, wl, fuzzy=False, threshold=85)
    assert res["universe"] == len(samples) * len(wl.keywords)
