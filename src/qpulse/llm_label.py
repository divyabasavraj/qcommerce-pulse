"""Label reviews with themes using a local LLM (Ollama).

uv run python -m qpulse.llm_label data/labels/llm_train_set.csv
uv run python -m qpulse.llm_label data/labels/hand_label_set.csv   # for measuring LLM accuracy

uv run python -m qpulse.llm_label data/labels/hand_label_set.csv --prompt v2

Results are cached per review in data/labels/llm_cache/<model>[-<prompt>].jsonl, so interrupted runs resume.
Output: data/labels/llm_labels_<model>[-<prompt>].csv (review_id + one 0/1 column per theme).
Prompt v1 keeps the original file names.
"""
import argparse
import json
import time

import pandas as pd
import requests

from qpulse.config import DATA
from qpulse.themes import THEME_KEYS, THEMES

LABEL_DIR = DATA / "labels"
OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "qwen2.5:7b"

INTRO = (
    "You classify Google Play reviews of Indian quick-commerce grocery apps (Blinkit, Zepto, "
    "BigBasket, Swiggy Instamart). Reviews may be English, Hindi or Hinglish.\n"
    "Pick every theme the review clearly mentions (one or more). Use 'other' only if no other theme fits.\n"
    "Themes:\n" + "\n".join(f"- {k}: {v}" for k, v in THEMES.items())
)

# v2 rules come from the theme definitions and disagreements on hand-set reviews 1-100 only;
# reviews 101-300 are held out for scoring.
RULES_V2 = """
Rules:
- Judge the text, not the star rating. A review that only says "good" or praises a delivery partner is positive, even at 1 star.
- Generic anger with no specific problem ("bad", "worst app", "very bad service", "cheating company") is other.
- refund_support needs a refund, return, cancellation or customer-support complaint in the text. Losing money to a wrong or damaged item alone is not refund_support.
- app_payment_bug is only for technical faults (crash, freeze, login/OTP, payment failure). A missing feature or policy (no cancel button, COD disabled) is not a bug.
- "Not delivering to my area", "service not available here" is availability_stock, not delivery_delay.
- An order cancelled by the app or never delivered is delivery_delay.
- Referral codes, coupons and offers not working are pricing_fees."""

PROMPTS = {
    "v1": INTRO + "\nReply with JSON only.",
    "v2": INTRO + RULES_V2 + "\nReply with JSON only.",
}

SCHEMA = {
    "type": "object",
    "properties": {"themes": {"type": "array", "items": {"type": "string", "enum": THEME_KEYS}}},
    "required": ["themes"],
}


def label_one(text: str, rating: int, model: str, prompt: str = "v1") -> list[str]:
    resp = requests.post(OLLAMA_URL, timeout=120, json={
        "model": model,
        "stream": False,
        "format": SCHEMA,
        "options": {"temperature": 0},
        "messages": [
            {"role": "system", "content": PROMPTS[prompt]},
            {"role": "user", "content": f"Rating: {rating} stars\nReview: {text}"},
        ],
    })
    resp.raise_for_status()
    themes = json.loads(resp.json()["message"]["content"]).get("themes", [])
    themes = [t for t in dict.fromkeys(themes) if t in THEME_KEYS]
    if len(themes) > 1 and "other" in themes:
        themes.remove("other")
    return themes or ["other"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--prompt", default="v1", choices=PROMPTS)
    args = parser.parse_args()

    df = pd.read_csv(args.input_csv)
    tag = args.model.replace(":", "-") + ("" if args.prompt == "v1" else f"-{args.prompt}")
    cache_path = LABEL_DIR / "llm_cache" / f"{tag}.jsonl"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache = {}
    if cache_path.exists():
        for line in cache_path.read_text().splitlines():
            row = json.loads(line)
            cache[row["review_id"]] = row["themes"]

    todo = df[~df["review_id"].isin(cache)]
    print(f"{len(df)} reviews, {len(df) - len(todo)} cached, {len(todo)} to label with {args.model}")
    started = time.time()
    with cache_path.open("a") as f:
        for i, row in enumerate(todo.itertuples(), 1):
            try:
                themes = label_one(str(row.text), int(row.rating), args.model, args.prompt)
            except Exception as e:
                print(f"  skip {row.review_id}: {type(e).__name__}")
                continue
            cache[row.review_id] = themes
            f.write(json.dumps({"review_id": row.review_id, "themes": themes}) + "\n")
            f.flush()
            if i % 100 == 0:
                rate = i / (time.time() - started)
                print(f"  {i}/{len(todo)}  {rate:.2f}/s  eta {(len(todo) - i) / rate / 60:.0f} min")

    out = pd.DataFrame({"review_id": df["review_id"]})
    for k in THEME_KEYS:
        out[k] = [int(k in cache.get(r, [])) for r in out["review_id"]]
    out = out[df["review_id"].isin(cache).values]
    all_labels = LABEL_DIR / f"llm_labels_{tag}.csv"
    if all_labels.exists():
        out = pd.concat([pd.read_csv(all_labels), out]).drop_duplicates("review_id", keep="last")
    out.to_csv(all_labels, index=False)
    print(f"wrote {all_labels} ({len(out)} rows)")


if __name__ == "__main__":
    main()
