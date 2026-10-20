"""Draw the labelling sets: uv run python -m qpulse.sample

data/labels/hand_label_set.csv  300 reviews, hand-labelled; the test set for every classifier
data/labels/llm_train_set.csv   3,000 reviews, LLM-labelled; training data for the fast classifier

The two sets don't overlap. Both are drawn from rows usable for theme metrics (see DATA_QUALITY.md)
and are stratified the same way: equal reviews per app, and within each app a fixed mix of star ratings
that over-weights 1-3★ so rarer complaint themes get enough examples. Theme shares measured on these
sets are therefore not population shares; the classifier report uses per-theme F1, which isn't affected.
"""
import pandas as pd

from qpulse.config import DATA, ROOT
from qpulse.db import connect

LABEL_DIR = DATA / "labels"
SEED = 20261020
# share of each app's sample per rating bucket
RATING_MIX = {"1-2": 0.55, "3": 0.15, "4-5": 0.30}


def stratified(df: pd.DataFrame, per_app: int, seed: int) -> pd.DataFrame:
    parts = []
    sizes = {b: round(per_app * share) for b, share in RATING_MIX.items()}
    sizes["4-5"] = per_app - sizes["1-2"] - sizes["3"]  # absorb rounding so each app gets exactly per_app
    for _, g in df.groupby("app"):
        for bucket, n in sizes.items():
            pool = g[g["bucket"] == bucket]
            parts.append(pool.sample(n=min(len(pool), n), random_state=seed))
    return pd.concat(parts).sample(frac=1, random_state=seed)


def main() -> None:
    con = connect()
    con.execute((ROOT / "sql" / "reviews_clean.sql").read_text())
    df = con.sql("""
        SELECT review_id, app, rating, review_date, text,
               CASE WHEN rating <= 2 THEN '1-2' WHEN rating = 3 THEN '3' ELSE '4-5' END AS bucket
        FROM reviews_clean
        WHERE NOT (is_repeated_text OR has_link OR is_empty_or_symbols)
    """).df()

    LABEL_DIR.mkdir(parents=True, exist_ok=True)
    hand_path = LABEL_DIR / "hand_label_set.csv"
    if hand_path.exists():
        # Never redraw the test set once labelling may have started.
        hand = pd.read_csv(hand_path)
        print(f"kept existing {hand_path} ({len(hand)} rows)")
    else:
        hand = stratified(df, per_app=75, seed=SEED)
        hand.drop(columns="bucket").to_csv(hand_path, index=False)
        print(f"wrote {hand_path} ({len(hand)} rows)")

    rest = df[~df["review_id"].isin(hand["review_id"])]
    train = stratified(rest, per_app=750, seed=SEED + 1)
    train.drop(columns="bucket").to_csv(LABEL_DIR / "llm_train_set.csv", index=False)
    print(f"wrote llm_train_set.csv ({len(train)} rows)")
    print(pd.crosstab(train["app"], train["bucket"]))


if __name__ == "__main__":
    main()
