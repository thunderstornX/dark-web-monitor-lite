"""Matcher-only eval over the labelled corpus.

Computes precision / recall / F1 on the (body, keyword) cell space
under two configurations:

  * exact-only mode  (fuzzy=False)
  * fuzzy-on mode    (fuzzy=True, threshold=85)

Both modes run offline; the eval is fully reproducible without
network access. The fuzzy-on mode is the one the matcher's CLI
default produces; the exact-only number is reported alongside so
the contribution of the fuzzy phase is visible."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))

from monitor.matcher import Watchlist, scan_body  # noqa: E402


def _short(p: Path) -> str:
    try:
        return str(p.relative_to(_REPO))
    except ValueError:
        return str(p)


def _confusion(samples: list[dict], watchlist: Watchlist,
                *, fuzzy: bool, threshold: int) -> dict:
    """Compute TP/FP/FN/TN over the (sample, keyword) cell space."""
    tp = fp = fn = tn = 0
    fp_cells: list[tuple[str, str]] = []
    fn_cells: list[tuple[str, str]] = []
    for s in samples:
        expected = set(s.get("expected") or [])
        matches = scan_body(
            s["body"], watchlist,
            source_url=s["id"], fuzzy=fuzzy, threshold=threshold,
        )
        observed = {m.keyword for m in matches}
        for kw in watchlist.keywords:
            actual = kw in expected
            predicted = kw in observed
            if actual and predicted:
                tp += 1
            elif (not actual) and predicted:
                fp += 1
                fp_cells.append((s["id"], kw))
            elif actual and (not predicted):
                fn += 1
                fn_cells.append((s["id"], kw))
            else:
                tn += 1
    universe = tp + fp + fn + tn
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = (2 * precision * recall / (precision + recall)
           if (precision + recall) else 0.0)
    accuracy = (tp + tn) / universe if universe else 0.0
    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "universe": universe,
        "precision": round(precision, 4),
        "recall":    round(recall, 4),
        "f1":        round(f1, 4),
        "accuracy":  round(accuracy, 4),
        "fp_cells":  fp_cells,
        "fn_cells":  fn_cells,
    }


def main() -> None:
    corpus_path = _REPO / "eval" / "labelled_corpus.json"
    out_dir = _REPO / "results"
    out_dir.mkdir(parents=True, exist_ok=True)

    raw = json.loads(corpus_path.read_text())
    keywords = raw["watchlist"]
    samples = raw["samples"]

    # Build a Watchlist via the matcher's loader, but we must manually
    # supply the disallowed-categories block to satisfy the policy
    # backstop (the eval corpus is not a real watchlist).
    from monitor.matcher import load_watchlist
    watchlist = load_watchlist({
        "iocs": keywords,
        "_disallowed_categories": [
            "personal_names",
            "residential_addresses",
            "government_or_military_aliases",
            "journalist_or_activist_identifiers",
            "lawyer_or_litigant_identifiers",
        ],
    })

    print(f"[eval] loaded {len(samples)} samples × "
          f"{len(watchlist.keywords)} keywords "
          f"= {len(samples) * len(watchlist.keywords)} cells")

    exact = _confusion(samples, watchlist, fuzzy=False, threshold=85)
    fuzzy = _confusion(samples, watchlist, fuzzy=True,  threshold=85)

    summary = {
        "n_samples":     len(samples),
        "n_keywords":    len(watchlist.keywords),
        "universe":      exact["universe"],
        "exact_only":    {k: v for k, v in exact.items()
                            if k not in ("fp_cells", "fn_cells")},
        "fuzzy_on":      {k: v for k, v in fuzzy.items()
                            if k not in ("fp_cells", "fn_cells")},
        "fp_fn_detail": {
            "exact_only": {"fp": exact["fp_cells"],
                            "fn": exact["fn_cells"]},
            "fuzzy_on":   {"fp": fuzzy["fp_cells"],
                            "fn": fuzzy["fn_cells"]},
        },
    }
    (out_dir / "eval_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True))

    raw_csv = out_dir / "eval_raw.csv"
    with raw_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["mode", "tp", "fp", "fn", "tn",
                     "precision", "recall", "f1", "accuracy"])
        for label, row in (("exact_only", exact), ("fuzzy_on", fuzzy)):
            w.writerow([label, row["tp"], row["fp"], row["fn"], row["tn"],
                         row["precision"], row["recall"], row["f1"],
                         row["accuracy"]])

    print(f"[eval] wrote {_short(out_dir / 'eval_summary.json')}")
    print(f"[eval] wrote {_short(raw_csv)}")
    for label, row in (("exact_only", exact), ("fuzzy_on", fuzzy)):
        print(f"[eval] {label:<11} "
               f"prec={row['precision']:.4f} "
               f"rec={row['recall']:.4f} "
               f"F1={row['f1']:.4f} "
               f"acc={row['accuracy']:.4f} "
               f"(tp={row['tp']} fp={row['fp']} "
               f"fn={row['fn']} tn={row['tn']})")


if __name__ == "__main__":
    main()
