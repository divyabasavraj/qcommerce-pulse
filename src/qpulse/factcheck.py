"""Check LLM-written report text against facts written by code (used by the weekly and monthly reports).

The LLM sees only `facts`: sentences written by code, each tied to one app (or none) and a status
("outside" / "inside" the expected range, or None). Its text is checked sentence by sentence: every number must
come from a fact about an app named in the same sentence (or a fact about no app), and "outside" / "inside" /
"within" the expected range must match those facts. One retry with the problems listed, then the caller's template.
"""
import re

import requests

from qpulse.config import APP_NAMES
from qpulse.llm_label import OLLAMA_URL

NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")
STARS = re.compile(r"\b[1-5](?:★|[- ]stars?\b)", re.I)  # "1★", "1-star": a name, not a number


def numbers(text: str) -> set[str]:
    return {n.replace(",", "").rstrip(".") for n in NUM.findall(STARS.sub("", text))}


SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def check_summary(summary: str, fact_list: list[dict]) -> list[str]:
    """Problems with the summary, sentence by sentence. Each number must come from a fact about an app named in
    the same sentence (or a fact about no app), and 'outside' / 'inside' the range must match those facts."""
    problems = []
    for sent in SENTENCE.split(summary.strip()):
        named = {k for k, v in APP_NAMES.items() if v.lower() in sent.lower()}
        usable = [f for f in fact_list if f["app"] is None or f["app"] in named]
        for n in sorted(numbers(sent)):
            if not any(n in numbers(f["text"]) for f in fact_list):
                problems.append(f'"{n}" is not in the facts')
            elif not any(n in numbers(f["text"]) for f in usable):
                problems.append(f'"{n}" belongs to a different app than the one named in: "{sent}"')
        for word, status in (("outside", "outside"), ("inside", "inside"), ("within", "inside")):
            if named and re.search(rf"\b{word}\b", sent, re.I) and not any(
                    f["status"] == status for f in usable if f["app"] is not None):
                problems.append(f'"{word}" the expected range is not true for the app named in: "{sent}"')
    return problems


def llm_summary(prompt: str, fact_list: list[dict], model: str) -> tuple[str | None, list[dict]]:
    """Ask the model for a summary; one retry naming the problems. Returns (summary or None, attempts)."""
    messages = [{"role": "user", "content": prompt + "\n".join(f"- {f['text']}" for f in fact_list)}]
    attempts = []
    for _ in range(2):
        resp = requests.post(OLLAMA_URL, json={
            "model": model, "stream": False, "messages": messages,
            "options": {"temperature": 0, "num_ctx": 8192},
        }, timeout=600)
        resp.raise_for_status()
        text = resp.json()["message"]["content"].strip()
        problems = check_summary(text, fact_list)
        attempts.append({"text": text, "problems": problems})
        if not problems:
            return text, attempts
        messages += [{"role": "assistant", "content": text},
                     {"role": "user", "content": "This summary has errors:\n" + "\n".join(f"- {p}" for p in problems)
                                                 + "\nRewrite it using only the facts, following the rules."}]
    return None, attempts
