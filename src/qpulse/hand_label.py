"""Terminal tool for hand-labelling the test set.

uv run python -m qpulse.hand_label

Type theme numbers separated by spaces (e.g. "1 2"), then Enter.
  b = back one review    n = add a note to the previous review    q = save and quit
Progress is saved after every review to data/labels/hand_labels.csv; rerun to resume.

uv run python -m qpulse.hand_label --review [N]

Re-check labels already given, starting at review N (default 1). Enter keeps the shown labels,
theme numbers replace them, q quits. Edits are saved after every review.
"""
import sys
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


def parse(ans: str) -> set[str] | None:
    try:
        picks = {THEME_KEYS[int(t) - 1] for t in ans.replace(",", " ").split()}
    except (ValueError, IndexError):
        print("  ? enter theme numbers 1-10, or b / n / q")
        return None
    if not picks:
        print("  ? pick at least one theme (10 = other)")
        return None
    return picks


def show(n: int, row, menu: str) -> None:
    print("\n" + "─" * 80)
    print(f"[{n}/300]  {row.app}  {'★' * int(row.rating)}{'☆' * (5 - int(row.rating))}")
    print(textwrap.fill(str(row.text), 80))
    print(f"\n{menu}")


def review(start: int) -> None:
    reviews = pd.read_csv(SET_PATH).set_index("review_id")
    done = load_done()
    menu = "  ".join(f"{i}={k}" for i, k in enumerate(THEME_KEYS, 1))
    j = start - 1
    while j < len(done):
        rid = done.at[j, "review_id"]
        show(j + 1, reviews.loc[rid], menu)
        current = [str(i) for i, k in enumerate(THEME_KEYS, 1) if int(done.at[j, k])]
        print(f"current: {' '.join(current)}  ({', '.join(THEME_KEYS[int(c) - 1] for c in current)})")
        ans = input("Enter = keep, numbers = replace, q = quit > ").strip().lower()
        if ans == "q":
            break
        if ans:
            picks = parse(ans)
            if picks is None:
                continue
            for k in THEME_KEYS:
                done.at[j, k] = int(k in picks)
            done.to_csv(OUT_PATH, index=False)
            print("  changed")
        j += 1
    print(f"\nreviewed up to {j}/{len(done)}; saved to {OUT_PATH}")


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--review":
        review(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
        return
    reviews = pd.read_csv(SET_PATH)
    done = load_done()
    menu = "  ".join(f"{i}={k}" for i, k in enumerate(THEME_KEYS, 1))
    i = 0
    while i < len(reviews):
        row = reviews.iloc[i]
        if row.review_id in set(done["review_id"]):
            i += 1
            continue
        show(len(done) + 1, row, menu)
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
        picks = parse(ans)
        if picks is None:
            continue
        new = {"review_id": row.review_id, **{k: int(k in picks) for k in THEME_KEYS}, "note": ""}
        done = pd.concat([done, pd.DataFrame([new])], ignore_index=True)
        done.to_csv(OUT_PATH, index=False)
        print(f"  saved: {', '.join(k for k in THEME_KEYS if k in picks)}")
        i += 1
    print(f"\nsaved {len(done)}/{len(reviews)} labels to {OUT_PATH}")
    print("\nThemes:\n" + "\n".join(f"  {i}. {k}: {THEMES[k]}" for i, k in enumerate(THEME_KEYS, 1)))


if __name__ == "__main__":
    main()
