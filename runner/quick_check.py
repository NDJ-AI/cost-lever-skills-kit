"""Single-turn spot-check: is a cheaper model good enough for THIS one step?

Most n8n / Zapier / script steps are single-turn -- one prompt in, one answer
out (summarize, classify, extract). For those you do NOT need the agentic eval
harness (run_eval.py). You need this: take a handful of real inputs, run them
through the current model and a cheaper candidate, and compare.

    python quick_check.py --spec my_step.json
    python quick_check.py --mock          # offline self-test, no key, no cost

Spec format (JSON):
{
  "prompt": "Classify sentiment as positive/negative/neutral.\\nText: {input}",
  "models": {"current": "claude-sonnet-5", "candidate": "claude-haiku-4-5-20251001"},
  "check": {"type": "label"},            # label | json | contains | none
  "cases": [
    {"input": "I love this",  "expect": "positive"},
    {"input": "total garbage", "expect": "negative"}
  ]
}

check.type:
  label    -> pass if `expect` appears (normalized) in the model's answer
  contains -> same as label; alias for readability on non-classification steps
  json     -> pass if the answer parses as JSON; if a case has "required_keys",
              all of them must be present
  none     -> no scoring; just print both answers side by side for you to judge
              (use this for summaries and other subjective steps)

The prompt uses {input} as the placeholder for each case's input text.
"""

import argparse
import json
import os
import sys

# Reuse the same pricing table + cost math as the big harness, so a $ figure
# here means the same thing it does there. PRICING is placeholders until filled.
try:
    from configs import PRICING, cost_for  # noqa: F401
except Exception:  # keep quick_check usable standalone if configs isn't importable
    PRICING = {}

    def cost_for(model, input_tokens, output_tokens):
        price = PRICING.get(model)
        if not price:
            return None
        pin, pout = price
        return (input_tokens / 1_000_000) * pin + (output_tokens / 1_000_000) * pout


# --- Backends -----------------------------------------------------------------

class AnthropicSingleTurn:
    """One prompt, one answer. Reads ANTHROPIC_API_KEY from the environment."""

    def __init__(self):
        import anthropic  # lazy, so --mock needs no dependency and no key
        self.client = anthropic.Anthropic()

    def run(self, model, prompt, max_tokens=1024):
        r = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(
            getattr(b, "text", "") for b in r.content if getattr(b, "type", None) == "text"
        )
        return text, (r.usage.input_tokens, r.usage.output_tokens)


class MockSingleTurn:
    """Scripted stand-in. `table[model]` is a function(prompt) -> answer text.

    Used only by --mock to prove the scorer discriminates a good model from a
    bad one with no API call. Token counts are faked so the cost column runs.
    """

    def __init__(self, table):
        self.table = table

    def run(self, model, prompt, max_tokens=1024):
        answer = self.table[model](prompt)
        return answer, (120, 8)


# --- Scoring ------------------------------------------------------------------

def _extract_json(text):
    """Pull the first {...} or [...] blob out of a model answer, tolerant of prose."""
    for open_c, close_c in (("{", "}"), ("[", "]")):
        i, j = text.find(open_c), text.rfind(close_c)
        if i != -1 and j != -1 and j > i:
            try:
                return json.loads(text[i : j + 1])
            except Exception:
                pass
    return json.loads(text)  # last resort: raises, caught by caller


def score(check_type, output, case):
    """Return True/False for an objective check, or None for subjective ('none')."""
    if check_type == "none":
        return None
    if check_type in ("label", "contains"):
        return str(case["expect"]).strip().lower() in output.lower()
    if check_type == "json":
        try:
            obj = _extract_json(output)
        except Exception:
            return False
        req = case.get("required_keys")
        if req:
            return isinstance(obj, dict) and all(k in obj for k in req)
        return True
    raise ValueError(f"unknown check type: {check_type!r}")


# --- Run ----------------------------------------------------------------------

def run_spec(backend, spec):
    prompt_tmpl = spec["prompt"]
    models = spec["models"]
    check_type = spec.get("check", {}).get("type", "none")
    cases = spec["cases"]

    rows = []
    for role, model in models.items():
        per_case = []
        for case in cases:
            prompt = prompt_tmpl.replace("{input}", str(case["input"]))
            answer, (tin, tout) = backend.run(model, prompt)
            per_case.append({
                "input": case["input"],
                "answer": answer.strip(),
                "passed": score(check_type, answer, case),
                "cost": cost_for(model, tin, tout),
            })
        rows.append({"role": role, "model": model, "cases": per_case})
    return check_type, rows


def _mean_cost(cases):
    xs = [c["cost"] for c in cases if c["cost"] is not None]
    return sum(xs) / len(xs) if xs else None


def report(check_type, rows):
    out = []
    objective = check_type != "none"

    if objective:
        out.append("")
        out.append(f"{'role':<12}{'model':<32}{'pass rate':>11}{'mean $/call':>14}")
        out.append("-" * 69)
        for r in rows:
            cases = r["cases"]
            n = len(cases)
            n_pass = sum(1 for c in cases if c["passed"])
            mc = _mean_cost(cases)
            cost = f"${mc:.5f}" if mc is not None else "n/a"
            out.append(f"{r['role']:<12}{r['model']:<32}{f'{n_pass}/{n}':>11}{cost:>14}")
        out.append("-" * 69)
        if any(c["cost"] is None for r in rows for c in r["cases"]):
            out.append("note: cost shows 'n/a' until PRICING is filled in configs.py.")

    # Side-by-side per case -- the useful part for subjective steps, and a good
    # sanity read even for objective ones (see WHERE they disagree).
    out.append("")
    out.append("PER-CASE COMPARISON")
    roles = [r["role"] for r in rows]
    for idx in range(len(rows[0]["cases"])):
        inp = rows[0]["cases"][idx]["input"]
        out.append("")
        out.append(f"  input: {str(inp)[:100]}")
        for r in rows:
            c = r["cases"][idx]
            mark = "" if c["passed"] is None else ("  [pass]" if c["passed"] else "  [FAIL]")
            out.append(f"    {r['role']:<10} {str(c['answer'])[:120]}{mark}")

    if objective:
        out.append("")
        out.append("Read pass-rate first. A candidate that matches the current model's")
        out.append("pass rate at lower cost is a real win; a gap of even 1-2 cases on")
        out.append("real inputs is your signal to keep the current model on this step.")
    else:
        out.append("")
        out.append("Subjective step: no auto-score. Read the pairs above. If the candidate")
        out.append("answers are as good on YOUR inputs, the cheaper model holds up here.")
    out.append("")
    return "\n".join(out)


# --- Offline self-test --------------------------------------------------------

def _mock_selftest():
    """Prove the scorer discriminates a good model from a bad one, no API key."""
    strong = "mock-strong"
    weak = "mock-weak"

    def strong_fn(prompt):
        p = prompt.lower()
        if "love" in p or "great" in p:
            return "positive"
        if "garbage" in p or "hate" in p or "terrible" in p:
            return "negative"
        return "neutral"

    def weak_fn(prompt):
        return "positive"  # a dumb model that always guesses positive

    spec = {
        "prompt": "Classify sentiment as positive/negative/neutral.\nText: {input}",
        "models": {"current": strong, "candidate": weak},
        "check": {"type": "label"},
        "cases": [
            {"input": "I love this",     "expect": "positive"},
            {"input": "total garbage",   "expect": "negative"},
            {"input": "it is fine",      "expect": "neutral"},
            {"input": "great work",      "expect": "positive"},
            {"input": "terrible service", "expect": "negative"},
        ],
    }

    # demo pricing so the cost column populates (illustrative, not real)
    PRICING[strong] = (3.0, 15.0)
    PRICING[weak] = (1.0, 5.0)

    backend = MockSingleTurn({strong: strong_fn, weak: weak_fn})
    check_type, rows = run_spec(backend, spec)
    print("MOCK SELF-TEST -- scripted answers, no API calls")
    print("(pricing shown is illustrative demo values, not real)")
    print(report(check_type, rows))

    by_role = {r["role"]: r for r in rows}
    cur_pass = sum(1 for c in by_role["current"]["cases"] if c["passed"])
    cand_pass = sum(1 for c in by_role["candidate"]["cases"] if c["passed"])
    assert cur_pass == 5, f"strong model should pass all 5, got {cur_pass}"
    assert cand_pass == 2, f"weak model should pass only the 2 positive cases, got {cand_pass}"
    print("SELF-TEST ASSERTIONS PASSED: scorer separates the good model (5/5) "
          "from the bad one (2/5).")


# --- CLI ----------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Single-turn cheaper-model spot-check")
    ap.add_argument("--spec", help="path to a spec JSON (prompt, models, check, cases)")
    ap.add_argument("--mock", action="store_true", help="run the offline self-test (no key, no cost)")
    ap.add_argument("--max-tokens", type=int, default=1024)
    args = ap.parse_args()

    if args.mock:
        _mock_selftest()
        return
    if not args.spec:
        ap.error("give --spec <file.json> for a real run, or --mock for the offline self-test")

    with open(args.spec) as f:
        spec = json.load(f)
    backend = AnthropicSingleTurn()
    check_type, rows = run_spec(backend, spec)
    print(report(check_type, rows))


if __name__ == "__main__":
    main()
