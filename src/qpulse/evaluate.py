"""Score predicted theme labels against hand labels.

uv run python -m qpulse.evaluate data/labels/llm_labels_qwen2.5-7b.csv  ->  docs/LABEL_EVAL.md
"""
import argparse
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from qpulse.config import DATA, ROOT
from qpulse.quality import md_table
from qpulse.themes import THEME_KEYS

HAND = DATA / "labels" / "hand_labels.csv"


def scores(truth: pd.DataFrame, pred: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for k in THEME_KEYS:
        t, p = truth[k].astype(bool), pred[k].astype(bool)
        tp, fp, fn = int((t & p).sum()), int((~t & p).sum()), int((t & ~p).sum())
        prec = tp / (tp + fp) if tp + fp else float("nan")
        rec = tp / (tp + fn) if tp + fn else float("nan")
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        rows.append({"theme": k, "support": int(t.sum()), "precision": prec, "recall": rec, "f1": f1})
    return pd.DataFrame(rows)


def macro_f1(truth: pd.DataFrame, pred: pd.DataFrame) -> float:
    s = scores(truth, pred)
    return s.loc[s["support"] > 0, "f1"].mean()


def bootstrap_ci(truth: pd.DataFrame, pred: pd.DataFrame, n: int = 1000) -> tuple[float, float]:
    """95% interval for macro-F1, resampling reviews with replacement."""
    rng = np.random.default_rng(0)
    vals = [macro_f1(truth.iloc[i], pred.iloc[i]) for i in (rng.integers(0, len(truth), len(truth)) for _ in range(n))]
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pred_csv")
    parser.add_argument("--out", default=str(ROOT / "docs" / "LABEL_EVAL.md"))
    args = parser.parse_args()

    truth = pd.read_csv(HAND)
    pred = pd.read_csv(args.pred_csv)
    ids = sorted(set(truth["review_id"]) & set(pred["review_id"]))
    truth = truth.set_index("review_id").loc[ids]
    pred = pred.set_index("review_id").loc[ids]
    if not ids:
        raise SystemExit("no overlap between hand labels and predictions; label the hand set with the model first")

    s = scores(truth, pred)
    f1 = macro_f1(truth, pred)
    lo, hi = bootstrap_ci(truth, pred)
    exact = (truth[THEME_KEYS].values == pred[THEME_KEYS].values).all(axis=1).mean()
    any_overlap = ((truth[THEME_KEYS].values & pred[THEME_KEYS].values).any(axis=1)).mean()

    shown = s.copy()
    for c in ["precision", "recall", "f1"]:
        shown[c] = shown[c].map(lambda v: "–" if pd.isna(v) else f"{v:.2f}")

    set_text = pd.read_csv(DATA / "labels" / "hand_label_set.csv").set_index("review_id")
    def names(row):
        return ", ".join(k for k in THEME_KEYS if row[k]) or "—"
    errors = pd.DataFrame({
        "text": [str(set_text.loc[i, "text"])[:90].replace("|", "/").replace("\n", " ") for i in ids],
        "hand": [names(truth.loc[i]) for i in ids],
        "model": [names(pred.loc[i]) for i in ids],
    })
    errors = errors[errors["hand"] != errors["model"]].head(15)

    report = "\n\n".join([
        f"# Theme labels vs hand labels: `{Path(args.pred_csv).name}`",
        f"_Generated {date.today().isoformat()} on {len(ids)} hand-labelled reviews._",
        f"**Macro-F1:** {f1:.2f} (95% CI {lo:.2f}–{hi:.2f}) · **Exact match (all themes right):** {100 * exact:.0f}% · "
        f"**At least one theme right:** {100 * any_overlap:.0f}%",
        md_table(shown),
        "## Disagreements (first 15)",
        md_table(errors) if len(errors) else "_none_",
    ]) + "\n"
    Path(args.out).write_text(report)
    print(report)


if __name__ == "__main__":
    main()
