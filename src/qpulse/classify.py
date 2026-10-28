"""Fast theme classifier (PLAN.md milestone 4): TF-IDF + one logistic regression per theme.

Trained on the 3,000 LLM-labelled reviews (qwen2.5-7b, prompt v2). Settings chosen on hand labels 1-100;
hand labels 101-300 are held out for scoring. Training takes seconds, so every run retrains from the
label files in git instead of storing a model file.

uv run python -m qpulse.classify              # label reviews with no themes yet -> data/themes.parquet
uv run python -m qpulse.classify --rebuild    # re-label every review
uv run python -m qpulse.classify --evaluate   # tuning grid + held-out score -> docs/CLASSIFIER_EVAL.md
"""
import argparse
import time
from datetime import date

import numpy as np
import pandas as pd
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from qpulse.config import DATA, ROOT
from qpulse.db import connect
from qpulse.evaluate import bootstrap_ci, macro_f1, scores
from qpulse.quality import md_table
from qpulse.themes import THEME_KEYS

LABELS = DATA / "labels"
TRAIN_TEXT = LABELS / "llm_train_set.csv"
TRAIN_LABELS = LABELS / "llm_labels_qwen2.5-7b-v2.csv"
THEMES_OUT = DATA / "themes.parquet"
EVAL_OUT = ROOT / "docs" / "CLASSIFIER_EVAL.md"

# Chosen on hand labels 1-100 (docs/CLASSIFIER_EVAL.md): highest tuning macro-F1 in the grid.
C = 10.0
THRESHOLD = 0.7
GRID_C = [0.3, 1, 3, 10]
GRID_THRESHOLD = [0.5, 0.6, 0.7]


class ThemeClassifier:
    def __init__(self, c: float = C, threshold: float = THRESHOLD):
        self.c, self.threshold = c, threshold
        # Word n-grams for vocabulary, character n-grams for Hinglish spelling variants ("bekar", "bekaar").
        self.words = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
        self.chars = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True)

    def fit(self, texts: list[str], y: np.ndarray) -> "ThemeClassifier":
        x = hstack([self.words.fit_transform(texts), self.chars.fit_transform(texts)]).tocsr()
        self.models = [LogisticRegression(C=self.c, class_weight="balanced", max_iter=2000).fit(x, y[:, j])
                       for j in range(len(THEME_KEYS))]
        return self

    def proba(self, texts: list[str]) -> np.ndarray:
        x = hstack([self.words.transform(texts), self.chars.transform(texts)]).tocsr()
        return np.column_stack([m.predict_proba(x)[:, 1] for m in self.models])

    def predict(self, texts: list[str], threshold: float | None = None) -> pd.DataFrame:
        p = self.proba(texts)
        out = (p >= (self.threshold if threshold is None else threshold)).astype(int)
        none = out.sum(axis=1) == 0
        out[none, p[none].argmax(axis=1)] = 1  # every review gets at least one theme, as in the hand labels
        return pd.DataFrame(out, columns=THEME_KEYS)


def texts(df: pd.DataFrame) -> list[str]:
    return df["text"].fillna("").astype(str).tolist()


def training_data() -> pd.DataFrame:
    # The v2 label file also holds the 300 hand-set reviews; the merge keeps only the 3,000 training reviews.
    df = pd.read_csv(TRAIN_TEXT).merge(pd.read_csv(TRAIN_LABELS), on="review_id")
    assert len(df) == 3000, len(df)
    return df


def hand_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Hand labels with text, split into tuning (rows 1-100) and held-out (rows 101-300)."""
    hand = pd.read_csv(LABELS / "hand_labels.csv").merge(
        pd.read_csv(LABELS / "hand_label_set.csv")[["review_id", "text"]], on="review_id", how="left")
    assert hand["text"].notna().all()
    return hand.iloc[:100].reset_index(drop=True), hand.iloc[100:].reset_index(drop=True)


def train(c: float = C, threshold: float = THRESHOLD) -> ThemeClassifier:
    df = training_data()
    return ThemeClassifier(c, threshold).fit(texts(df), df[THEME_KEYS].values)


def label_reviews(rebuild: bool = False) -> None:
    t0 = time.time()
    con = connect()
    reviews = con.sql("SELECT review_id, text FROM reviews").df()
    old = pd.read_parquet(THEMES_OUT) if THEMES_OUT.exists() and not rebuild else None
    todo = reviews if old is None else reviews[~reviews["review_id"].isin(old["review_id"])]
    if todo.empty:
        print(f"no new reviews to label ({len(old):,} already in {THEMES_OUT.relative_to(ROOT)})")
        return
    clf = train()
    new = pd.concat([todo[["review_id"]].reset_index(drop=True), clf.predict(texts(todo))], axis=1)
    out = new if old is None else pd.concat([old, new], ignore_index=True)
    out.to_parquet(THEMES_OUT, index=False)
    print(f"labelled {len(new):,} reviews ({len(out):,} total) in {time.time() - t0:.0f}s -> {THEMES_OUT.relative_to(ROOT)}")


def evaluate() -> None:
    tune, test = hand_data()
    grid = []
    for c in GRID_C:
        clf = train(c)
        p = {t: clf.predict(texts(tune), t) for t in GRID_THRESHOLD}
        grid.append({"C": c, **{f"threshold {t}": f"{macro_f1(tune[THEME_KEYS], p[t]):.3f}" for t in GRID_THRESHOLD}})

    clf = train()
    pred = clf.predict(texts(test))
    truth = test[THEME_KEYS]
    llm = pd.read_csv(TRAIN_LABELS).set_index("review_id").loc[test["review_id"], THEME_KEYS].reset_index(drop=True)

    def summary(name: str, p: pd.DataFrame) -> dict:
        lo, hi = bootstrap_ci(truth, p)
        return {"labeller": name, "macro-F1": f"{macro_f1(truth, p):.2f}", "95% CI": f"{lo:.2f}–{hi:.2f}",
                "exact match": f"{100 * (truth.values == p.values).all(axis=1).mean():.0f}%"}

    # Paired bootstrap: same resampled reviews for both labellers.
    rng = np.random.default_rng(0)
    diffs = []
    for _ in range(1000):
        i = rng.integers(0, len(test), len(test))
        diffs.append(macro_f1(truth.iloc[i], pred.iloc[i]) - macro_f1(truth.iloc[i], llm.iloc[i]))
    d_lo, d_hi = np.percentile(diffs, [2.5, 97.5])

    per_theme = scores(truth, pred)[["theme", "support", "precision", "recall", "f1"]].merge(
        scores(truth, llm)[["theme", "f1"]].rename(columns={"f1": "LLM f1"}), on="theme")
    for col in ["precision", "recall", "f1", "LLM f1"]:
        per_theme[col] = per_theme[col].map(lambda v: "–" if pd.isna(v) else f"{v:.2f}")

    t0 = time.time()
    clf.predict(texts(training_data()))
    speed = 3000 / (time.time() - t0)

    report = f"""# Fast theme classifier

_Generated {date.today().isoformat()} by `uv run python -m qpulse.classify --evaluate`._

TF-IDF (word 1–2-grams + character 2–5-grams) with one logistic regression per theme (balanced class
weights), trained on the 3,000 reviews labelled by qwen2.5-7b with prompt v2. A theme is on when its
probability is at least the threshold; a review with no theme over the threshold gets its most likely one.

## Settings chosen on hand labels 1–100 (macro-F1)

{md_table(pd.DataFrame(grid))}

Chosen: C = {C}, threshold = {THRESHOLD}. The 100 tuning reviews are few, so differences of 0.01–0.02 in this grid are noise.

## Held-out score: hand labels 101–300 ({len(test)} reviews)

{md_table(pd.DataFrame([summary("fast classifier", pred), summary("LLM qwen2.5-7b v2 (its teacher)", llm)]))}

Classifier minus LLM, paired bootstrap: {np.mean(diffs):+.2f} macro-F1 (95% CI {d_lo:+.2f} to {d_hi:+.2f}).

Speed: about {speed:,.0f} reviews/s on one laptop CPU, against 1–2 reviews/s for the LLM (docs/PROJECT_LOG.md).

{md_table(per_theme)}
"""
    EVAL_OUT.write_text(report)
    print(report)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--evaluate", action="store_true")
    args = parser.parse_args()
    if args.evaluate:
        evaluate()
    else:
        label_reviews(args.rebuild)


if __name__ == "__main__":
    main()
