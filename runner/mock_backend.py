"""Mock backend + offline self-test.

Proves the harness plumbing (agent loop, tools, advisor path, scorer, cost
aggregation, report) end to end with NO API key and NO cost, by scripting the
model's responses instead of calling one. Run directly:

    python mock_backend.py

The one seam this does NOT cover is the live model call itself — that's what a
real `python run_eval.py --fixture ... --runs 5` exercises with your key.
"""

import os
import tempfile

import configs
from configs import Config, HAIKU, SONNET, OPUS
from executor import run_config
from tools import setup_workdir, score_objective
from run_eval import report


# --- Minimal stand-ins for the SDK response shape -----------------------------

class _Block:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _Usage:
    def __init__(self, i, o):
        self.input_tokens = i
        self.output_tokens = o


class _Resp:
    def __init__(self, stop_reason, content, usage):
        self.stop_reason = stop_reason
        self.content = content
        self.usage = usage


class MockBackend:
    """Returns scripted responses. Empty `tools` => it's an advisor consult."""

    ADVICE = (
        "Don't split on operators — that loses precedence. Tokenize, then use a "
        "recursive-descent parser: expression -> term -> factor, handle unary minus "
        "in factor, and let division raise ZeroDivisionError naturally. Consult me "
        "again before you declare done."
    )

    def __init__(self, script):
        self.script = script
        self.i = 0

    def create(self, model, max_tokens, system, tools, messages):
        if not tools:  # advisor consult
            return _Resp("end_turn", [_Block(type="text", text=self.ADVICE)], _Usage(320, 110))
        if self.i >= len(self.script):
            return _Resp("end_turn", [_Block(type="text", text="done")], _Usage(400, 30))
        action = self.script[self.i]
        self.i += 1
        if action[0] == "text":
            return _Resp("end_turn", [_Block(type="text", text=action[1])], _Usage(500, 50))
        _, name, inp = action
        block = _Block(type="tool_use", id=f"tu_{self.i}", name=name, input=inp)
        return _Resp("tool_use", [block], _Usage(520, 80))


# --- A deliberately wrong implementation (naive, no precedence/unary) ----------

BUGGY_SOURCE = '''\
import re


def evaluate(expr: str) -> float:
    expr = expr.replace(" ", "")
    tokens = re.findall(r"\\d+\\.?\\d*|[+\\-*/]", expr)
    if not tokens:
        raise ValueError("empty")
    result = float(tokens[0])
    i = 1
    while i < len(tokens):
        op = tokens[i]
        val = float(tokens[i + 1])
        i += 2
        if op == "+":
            result += val
        elif op == "-":
            result -= val
        elif op == "*":
            result *= val
        else:
            result /= val
    return result
'''


def _fixture_dir():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, "..", "example_fixture", "fixture_expr_eval"))


def _reference_source(fixture_dir):
    with open(os.path.join(fixture_dir, "solution", "evaluator_solution.py")) as f:
        return f.read()


def main():
    fixture = _fixture_dir()
    ref = _reference_source(fixture)

    # DEMO-ONLY pricing so the cost column populates. These are illustrative,
    # not real prices — the point is to show the math runs, not to quote a figure.
    configs.PRICING = {HAIKU: (1.0, 5.0), SONNET: (3.0, 15.0), OPUS: (15.0, 75.0)}

    good = [
        ("tool", "read_file", {"path": "TASK.md"}),
        ("tool", "write_file", {"path": "calc/evaluator.py", "content": ref}),
        ("tool", "run_tests", {}),
        ("text", "All tests pass."),
    ]
    buggy = [
        ("tool", "read_file", {"path": "TASK.md"}),
        ("tool", "write_file", {"path": "calc/evaluator.py", "content": BUGGY_SOURCE}),
        ("tool", "run_tests", {}),
        ("text", "Looks done to me."),
    ]
    good_with_advisor = [
        ("tool", "read_file", {"path": "TASK.md"}),
        ("tool", "consult_advisor", {"question": "How do I respect precedence and unary minus?"}),
        ("tool", "write_file", {"path": "calc/evaluator.py", "content": ref}),
        ("tool", "run_tests", {}),
        ("text", "Tests pass after taking the advice."),
    ]

    # Three scripted configs standing in for the real triplet.
    plan = [
        (Config("haiku-solo", HAIKU, None), buggy),                 # cheap alone: fails
        (Config("haiku+opus", HAIKU, OPUS), good_with_advisor),     # cheap + advisor: passes
        (Config("sonnet-solo", SONNET, None), good),                # stronger alone: passes
    ]
    configs_used = [c for c, _ in plan]

    n_runs = 3
    workroot = tempfile.mkdtemp(prefix="mock_eval_")
    results = {}
    for config, script in plan:
        runs = []
        for r in range(n_runs):
            wd = os.path.join(workroot, f"{config.name}_run{r}")
            setup_workdir(fixture, wd)
            backend = MockBackend(list(script))  # fresh script cursor per run
            outcome = run_config(backend, config, wd, max_turns=25)
            score = score_objective(wd)
            from run_eval import combined_cost
            runs.append({
                "score": score,
                "usage": outcome["usage"],
                "turns": outcome["turns"],
                "advisor_calls": outcome["advisor_calls"],
                "stop": outcome["stop"],
                "cost": combined_cost(config, outcome["usage"]),
            })
        results[config.name] = runs

    print("MOCK SELF-TEST — scripted responses, no API calls")
    print("(pricing shown is illustrative demo values, not real)")
    print(report(results, configs_used))

    # Assert the plumbing actually discriminates correct from buggy.
    haiku_pass = sum(r["score"]["passed"] for r in results["haiku-solo"])
    advisor_pass = sum(r["score"]["passed"] for r in results["haiku+opus"])
    advisor_consults = results["haiku+opus"][0]["advisor_calls"]
    assert haiku_pass == 0, "buggy executor should fail all runs"
    assert advisor_pass == n_runs, "advisor run should pass all runs"
    assert advisor_consults >= 1, "advisor should have been consulted"
    print("SELF-TEST ASSERTIONS PASSED: scorer distinguishes correct vs buggy; advisor path fired.")


if __name__ == "__main__":
    main()
