"""Terminal tool for hand-labelling the test set.

uv run python -m qpulse.hand_label

Type theme numbers separated by spaces (e.g. "1 2"), then Enter.
  b = back one review    n = add a note to the previous review    q = save and quit
Progress is saved after every review to data/labels/hand_labels.csv; rerun to resume.
"""
import textwrap

import pandas as pd

from qpulse.config import DATA
from qpulse.themes import THEME_KEYS, THEMES

LABEL_DIR = DATA / "labels"
SET_PATH = LABEL_DIR / "hand_label_set.csv"
OUT_PATH = LABEL_DIR / "hand_labels.csv"


def load_done() -> pd.DataFrame:
    if OUT_PATH.exists():
        return pd.read_csv(OUT_PATH, dtype={"note": str}, keep_default_na=False)
    return pd.DataFrame(columns=["review_id", *THEME_KEYS, "note"])


def main() -> None:
    reviews = pd.read_csv(SET_PATH)
    done = load_done()
    menu = "  ".join(f"{i}={k}" for i, k in enumerate(THEME_KEYS, 1))
    i = 0
    while i < len(reviews):
        row = reviews.iloc[i]
        if row.review_id in set(done["review_id"]):
            i += 1
            continue
        print("\n" + "─" * 80)
        print(f"[{len(done) + 1}/{len(reviews)}]  {row.app}  {'★' * int(row.rating)}{'☆' * (5 - int(row.rating))}")
        print(textwrap.fill(str(row.text), 80))
        print(f"\n{menu}")
        ans = input("> ").strip().lower()
        if ans == "q":
            break
        if ans == "b":
            if len(done):
                last_id = done.iloc[-1].review_id
                done = done.iloc[:-1]
                done.to_csv(OUT_PATH, index=False)
                i = int((reviews["review_id"] == last_id).idxmax())
            continue
        if ans == "n":
            if len(done):
                done.loc[done.index[-1], "note"] = input("note> ").strip()
                done.to_csv(OUT_PATH, index=False)
            continue
        try:
            picks = {THEME_KEYS[int(t) - 1] for t in ans.replace(",", " ").split()}
        except (ValueError, IndexError):
            print("  ? enter theme numbers 1-10, or b / n / q")
            continue
        if not picks:
            print("  ? pick at least one theme (10 = other)")
            continue
        new = {"review_id": row.review_id, **{k: int(k in picks) for k in THEME_KEYS}, "note": ""}
        done = pd.concat([done, pd.DataFrame([new])], ignore_index=True)
        done.to_csv(OUT_PATH, index=False)
        i += 1
    print(f"\nsaved {len(done)}/{len(reviews)} labels to {OUT_PATH}")
    print("\nThemes:\n" + "\n".join(f"  {i}. {k}: {THEMES[k]}" for i, k in enumerate(THEME_KEYS, 1)))


if __name__ == "__main__":
    main()
