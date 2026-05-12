# Eval results

Live numbers from `python eval/run_eval.py`, the rules-only matcher
eval over the labelled 55-sample × 10-keyword corpus
(550 (sample, keyword) cells).

## Method

`eval/labelled_corpus.json` contains 55 synthetic bodies plus 10
watchlist keywords. Each body carries an `expected` list naming the
watchlist entries it should fire. The harness:

1. Runs the matcher in **exact-only** mode (`fuzzy=False`).
2. Runs the matcher in **fuzzy-on** mode (`fuzzy=True, threshold=85`).
3. Compares observed vs. expected for every cell, computes TP/FP/FN/TN
   and the derived precision/recall/F1/accuracy.

The corpus mixes five classes by design:

| Class    | Count | What it stresses                                        |
|----------|------:|---------------------------------------------------------|
| exact-*  | 10    | direct substring matches                                |
| fuzzy-*  | 10    | typos, case shifts, hyphen/space variants               |
| noise-*  | 10    | unrelated bodies — must NOT fire (precision pressure)   |
| tricky-* | 10    | typos pretending to match, negations, abbreviations     |
| long-*   |  5    | long bodies where matches are diluted by surrounding text |
| url-*    |  5    | URL-shaped bodies (different tokenisation)              |
| negation-* | 2   | bodies that say "not X" (matcher cannot read intent)    |
| bilingual-*| 3   | non-English bodies with embedded English brand names    |

Total: 55 samples × 10 keywords = 550 cells.

## Reproducing

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python eval/run_eval.py
```

The eval is offline-only and deterministic; re-runs produce
identical numbers.

## Latest measured numbers (2026-05-12)

### Aggregate

| Mode        | TP | FP | FN | TN  | Precision | Recall | F1     | Accuracy |
|-------------|---:|---:|---:|----:|----------:|-------:|-------:|---------:|
| exact_only  | 29 |  1 | 13 | 507 | 0.9667    | 0.6905 | 0.8056 | 0.9745   |
| **fuzzy_on**| **41** | **6** | **1** | **502** | **0.8723** | **0.9762** | **0.9213** | **0.9873** |

The fuzzy-on mode trades a small amount of precision (–9 pp) for a
large gain in recall (+29 pp); F1 improves from 0.81 to **0.92**.

## Reading the numbers

* **Exact-only** is conservative by construction: it cannot miss an
  exact substring (1 FP only — a case-folding edge), but it cannot
  see typo'd or rephrased forms either (13 FNs). It is the safe
  default for environments where every alert costs analyst time.
* **Fuzzy-on** uses a strict per-token min-aggregation scorer for
  multi-word keywords (every keyword token must have a
  near-equivalent body token), `fuzz.ratio` against tokens AND
  joined-token pairs for single-word keywords, and a 5-character
  minimum for single-word fuzzy entries. The 7 residual
  mispredictions are all defensible:

  | Sample      | Cell                  | Why                                |
  |-------------|-----------------------|------------------------------------|
  | fuzzy-09    | FP: `FictionalCo`     | rapidfuzz scores "fictional" ≈85 against "FictionalCo" — borderline at the threshold boundary |
  | tricky-02   | FP: `PRJ-AURORA`      | body has "PRJ-Auror" + explicit negation "not our codename"; matcher cannot read intent |
  | tricky-04   | FP: `FCo`             | case-folding: body "FCO" exact-matches watchlist "FCo" — operator-correct behaviour |
  | tricky-06   | FP: `Project Aurora`  | body has "Project Auroras" (plural variant) — matcher reasonably fires |
  | tricky-09   | FPs: `Project Aurora`, `Aurora-Zenith` | body has all required tokens; the negation word "without" is not understood |
  | url-02      | FN: `ExampleInc`      | URL token "example-inc.example" atomises to "example", "inc", "example" — the joined-pair fix is single-pass and does not handle three-atom joins |

  We deliberately do **not** tune the matcher further. Each
  residual reflects an honest limit of pattern matching: matchers
  cannot read negation, plural variants always look similar to the
  singular, and operator-friendly case-insensitive matching is the
  right behaviour even when a strict label disagrees.

## What this eval does *not* claim

* It does **not** measure live onion fetching, Tor circuit health,
  or webhook delivery. Those paths are tested under mocked HTTP
  only. The deliberate choice keeps the eval reproducible offline.
* It does **not** measure latency. The matcher runs every cell
  in well under a millisecond; performance is not the contribution.
* It does **not** validate severity bands. Match.score is a
  rapidfuzz number; the operator decides how to bucket it.
* It does **not** measure long-term recall on a real CTI feed.
  Five-class synthetic samples are a unit-test, not a benchmark of
  the underground.
